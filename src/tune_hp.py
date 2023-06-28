'''
  A script that is part of the data pipeline to find optimal hyperparameters.
  
  Author: Jackson Howe
  Date Created: June 27, 2023
  Last Updated: June 27, 2023
'''

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications.resnet50 import preprocess_input
import pandas as pd

# Have to install keras with a subprocess because for some reason I get a 
# ModuleNotFoundError otherwise (June 27, 2023)
import sys
import subprocess

# implement pip as a subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'keras-tuner'])

import keras_tuner as kt

tf.compat.v1.disable_eager_execution()
        
def model_builder(hp):
  # Build model
  model = tf.keras.Sequential()

  # Transfer learning
  model.add(tf.keras.applications.ResNet50(include_top = False, pooling = 'avg', weights ='imagenet'))
  
  # 2nd layer as Dense for 2-class classification
  model.add(tf.keras.layers.Dense(2, activation = 'relu'))
  
  # Not training the resnet on the new data set. Using the pre-trained weigths
  model.layers[0].trainable = False
  
  # Tune the learning rate for the optimizer
  # Choose and optimal value from 0.01, 0.001, 0.005, 0.0001, 0.0005
  hp_learning_rate = hp.Choice(
    'learning_rate', 
    values=[1e-2, 1e-3, 5e-3, 1e-4, 5e-4])  
  
  # compile the model
  model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=hp_learning_rate), 
    loss=keras.losses.BinaryCrossentropy(), 
    metrics = ['accuracy'])

  return model

if __name__ == '__main__':
  # Create data generator
  datagen = ImageDataGenerator(
    rescale=1/255,
    preprocessing_function=preprocess_input
  )
  
  # Training dataset
  train_ds = datagen.flow_from_directory(
    '/scratch/jhowe4/outputs/GDC/paad_example2/train',
    target_size=(224, 224),
    class_mode='binary'
  )
  
  # Testing dataset
  test_ds = datagen.flow_from_directory(
    '/scratch/jhowe4/outputs/GDC/paad_example2/test',
    target_size=(224, 224),
    class_mode='binary'
  )
  
  # Validation dataset
  valid_ds = datagen.flow_from_directory(
    '/scratch/jhowe4/outputs/GDC/paad_example2/valid',
    target_size=(224, 224),
    class_mode='binary'
  )
  
  # Instanstiate the tuner
  tuner = kt.Hyperband(
    model_builder,
    objective='val_accuracy',
    max_epochs=10,
    factor=3,
    directory='../outputs/hp',
    project_name='2023-06-27')
  
  # Create a callback to stop training early after reaching a certain value for 
  # the validatoin loss
  stop_early = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5)
  
  # Run the hyperparameter search. The arguments for the search method are the 
  # same as those used in model.fit
  tuner.search(
    train_ds,
    steps_per_epoch=16,
    validation_data=valid_ds,
    validation_steps=16,
    epochs=4
  )
  
  # Get the optimal hyperparameters
  best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
  
  print(f"""
  The hyperparameter seach is complete. The optimal learning rate for the 
  optimizer is {best_hps.get('learning_rate')}.
        """)
  
  # Build the model
  model = tuner.hypermodel.build(best_hps)
  
  # Fit the model on a max number of epochs of 50
  fit_history = model.fit(
    train_ds,
    steps_per_epoch=4,
    validation_data=valid_ds,
    validation_steps=4,
    epochs=3
  )
  
  # Find the optimal number of epochs to train the model with the 
  # hyperparameters obtained from the search
  val_acc_per_epoch = fit_history.history['val_accuracy']
  best_epoch = val_acc_per_epoch.index(max(val_acc_per_epoch)) + 1
  print('Best epoch: %d' % (best_epoch,))
  
  hypermodel = tuner.hypermodel.build(best_hps)
  
  # Retrain the model
  hypermodel.fit(
    train_ds,
    steps_per_epoch=16,
    validation_data=valid_ds,
    validation_steps=16,
    epochs=best_epoch
  )
  
  # Save the model weights
  hypermodel.save_weights('../model/tf-2023-06-27/weights.h5')
  
  # Evaluate model performance
  eval_result = hypermodel.evaluate(
    test_ds,
    steps=len(test_ds)
  )
  print("[test loss, test accuracy]:", eval_result)
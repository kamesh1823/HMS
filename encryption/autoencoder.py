import os
IMG_SIZE  = 224
IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 1)
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'autoencoder.keras')

def _keras():
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    return tf, keras, layers, Model

def build_encoder(input_shape=IMG_SHAPE):
    _, keras, layers, Model = _keras()
    inp = keras.Input(shape=input_shape)
    x = layers.Conv2D(32,(3,3),activation='relu',padding='same')(inp)
    x = layers.BatchNormalization()(x); x = layers.MaxPooling2D((2,2))(x)
    x = layers.Conv2D(64,(3,3),activation='relu',padding='same')(x)
    x = layers.BatchNormalization()(x); x = layers.MaxPooling2D((2,2))(x)
    x = layers.Conv2D(128,(3,3),activation='relu',padding='same')(x)
    x = layers.BatchNormalization()(x); x = layers.MaxPooling2D((2,2))(x)
    x = layers.Conv2D(256,(3,3),activation='relu',padding='same')(x)
    x = layers.BatchNormalization()(x)
    return Model(inp, x, name='encoder')

def build_decoder():
    _, keras, layers, Model = _keras()
    inp = keras.Input(shape=(28,28,256))
    x = layers.Conv2DTranspose(128,(3,3),strides=2,activation='relu',padding='same')(inp)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2DTranspose(64,(3,3),strides=2,activation='relu',padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2DTranspose(32,(3,3),strides=2,activation='relu',padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(1,(1,1),activation='sigmoid')(x)
    return Model(inp, x, name='decoder')

def build_autoencoder():
    _, keras, layers, Model = _keras()
    enc = build_encoder(); dec = build_decoder()
    inp = keras.Input(shape=IMG_SHAPE)
    ae  = Model(inp, dec(enc(inp)), name='autoencoder')
    ae.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return ae, enc, dec

def save_model(ae, enc, dec):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    ae.save(MODEL_PATH.replace('.keras','_full.keras'))
    enc.save(MODEL_PATH.replace('.keras','_encoder.keras'))
    dec.save(MODEL_PATH.replace('.keras','_decoder.keras'))

def load_models():
    _, keras, _, _ = _keras()
    ep = MODEL_PATH.replace('.keras','_encoder.keras')
    dp = MODEL_PATH.replace('.keras','_decoder.keras')
    if not os.path.exists(ep): raise FileNotFoundError(f"Model not found. Run train_model.py first.")
    return keras.models.load_model(ep), keras.models.load_model(dp)

def models_exist():
    return os.path.exists(MODEL_PATH.replace('.keras','_encoder.keras'))

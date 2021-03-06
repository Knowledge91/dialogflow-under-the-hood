try:
    import unzip_requirements
except ImportError:
    pass
import json
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras import layers
import numpy as np
import random

# Hyperparameters
oov_tok = "<OOV>"
num_epochs = 300
threshold = 0.5

# Load Intents
with open("./intents.json", "r") as f:
    intents = json.load(f)

## Gather and Tokenize Intents, Labels to One-Hot presentation
intent_list = []
label_list = []
for index, intent in enumerate(intents):
    intent_list += intent["patterns"]
    num_patterns = len(intent["patterns"])
    label_list += [index] * num_patterns

tokenizer = Tokenizer(oov_token=oov_tok)
tokenizer.fit_on_texts(intent_list)
word_index = tokenizer.word_index
sequences = tokenizer.texts_to_sequences(intent_list)
max_length = len(max(sequences, key=len))
vocab_size = len(word_index)
padded = pad_sequences(sequences)
padded_length = len(padded[0])
labels = tf.keras.utils.to_categorical(label_list)
num_categories = len(labels[0])

## Model
model = tf.keras.Sequential(
    [
        layers.Embedding(vocab_size + 1, 16, input_length=padded_length),
        layers.Flatten(),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.5),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.5),
        layers.Dense(num_categories, activation="softmax"),
    ]
)
model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["acc"])
model.fit(padded, labels, epochs=num_epochs, verbose=2)


def inferHandler(event, context):
    # if boyd is dict => we invoke local
    if type(event["body"]) != dict:
        body = json.loads(event["body"])
    else:
        body = event["body"]

    sentence = body["msg"]
    sequence = tokenizer.texts_to_sequences([sentence])
    padded_sequence = pad_sequences(sequence, maxlen=padded_length)
    prediction = model.predict(padded_sequence)[0]
    print(sentence, prediction)

    # if none of the categories has a categories has a probability > threshold
    # return default
    if prediction[np.argmax(prediction)] < threshold:
        body["intent"] = "default"
        body["response"] = "Sry but I did not understand"
    else:
        intent = intents[np.argmax(prediction)]
        tag = intent["tag"]
        body["intent"] = tag
        body["response"] = random.choice(intent["responses"])

    response = {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }

    return response

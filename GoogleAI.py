import google.generativeai as genai

genai.configure(api_key="")

models = genai.list_models()

for model in models:
    if "generateContent" in model.supported_generation_methods:
        print(model.name)


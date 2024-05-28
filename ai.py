from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from diffusers import DiffusionPipeline
from transformers import AutoModelForSeq2SeqLM
from samplings import top_p_sampling, temperature_sampling
import torch
from sentence_transformers import SentenceTransformer, util
from datasets import load_dataset
import soundfile as sf
import unicodedata
import itertools


class AIAssistant:
    def __init__(self):
        pass


    ## generate regexp for search over memory
    def gen_search_expr(self,palabras_unidas):

        combinaciones = []

        for i in range(1, len(palabras_unidas) + 1):
            for combinacion in itertools.combinations(palabras_unidas, i):
                regex = ".*?".join(combinacion)
                combinaciones.append(regex)

        return combinaciones

    ## join taggued tokens into words
    def process_list(self,lista):
        palabras_unidas = []
        palabra_actual = ""

        for token in lista:
            if token.startswith("##"):
                palabra_actual += token[2:]
            else:
                if palabra_actual:
                    palabras_unidas.append(palabra_actual)
                    palabra_actual = ""
                palabra_actual += token

        if palabra_actual:
            palabras_unidas.append(palabra_actual)

        return [unicodedata.normalize("NFKD", palabra).encode("ASCII", "ignore").decode("ASCII").lower() for palabra in palabras_unidas]

   
    ## gramatical classificator
    def grammatical_pos_tagger(self, text):
        nlp_pos = pipeline("token-classification", model="QCRI/bert-base-multilingual-cased-pos-english", tokenizer="QCRI/bert-base-multilingual-cased-pos-english")
        res = nlp_pos(text)
        return res


    ## entity classifier
    def entity_pos_tagger(self, txt):
        tokenizer = AutoTokenizer.from_pretrained("Davlan/bert-base-multilingual-cased-ner-hrl")
        model = AutoModelForTokenClassification.from_pretrained("Davlan/bert-base-multilingual-cased-ner-hrl")
        nlp = pipeline("ner", model=model, tokenizer=tokenizer)
        ner_results = nlp(txt)
        return ner_results


    ## sentiment analysis
    def sentiment_tags(self,text):
        distilled_student_sentiment_classifier = pipeline(
            model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
            return_all_scores=True
        )

        # english
        return distilled_student_sentiment_classifier(text)

    ## check similarity among sentences (group of tokens (words))
    def similarity_tag(self, sentenceA,sentenceB):
        res=[]
        model = SentenceTransformer('abbasgolestani/ag-nli-bert-mpnet-base-uncased-sentence-similarity-v1') 

        # Two lists of sentences
        #sentences1 = ['I am honored to be given the opportunity to help make our company better',
        #            'I love my job and what I do here',
        #            'I am excited about our company’s vision']

        #sentences2 = ['I am hopeful about the future of our company',
        #            'My work is aligning with my passion',
        #            'Definitely our company vision will be the next breakthrough to change the world and I’m so happy and proud to work here']

        sentences1 = sentenceA
        sentences2 = sentenceB
        #Compute embedding for both lists
        embeddings1 = model.encode(sentences1, convert_to_tensor=True)
        embeddings2 = model.encode(sentences2, convert_to_tensor=True)

        #Compute cosine-similarities
        cosine_scores = util.cos_sim(embeddings1, embeddings2)

        #Output the pairs with their score
        for i in range(len(sentences1)):
            try:
                res.append({"A": sentences1[i], "B":sentences2[i], "score":cosine_scores[i][i]})
            except:
                pass

            #print("{} \t\t {} \t\t Score: {:.4f}".format(sentences1[i], sentences2[i], cosine_scores[i][i]))

        return res



    ## text to speech
    def texto_to_speech(self,txt):    
        synthesiser = pipeline("text-to-speech", "microsoft/speecht5_tts")

        embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        speaker_embedding = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
        # You can replace this embedding with your own as well.

        speech = synthesiser(txt, forward_params={"speaker_embeddings": speaker_embedding})
        sf.write("speech.wav", speech["audio"], samplerate=speech["sampling_rate"])

        return speech   
    ## text to stable difusor generated image
    def text_to_image_generation(self, prompt, n_steps=40, high_noise_frac=0.8):
        base = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, variant="fp16", use_safetensors=True
        )
        base.to("cuda")
        refiner = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=base.text_encoder_2,
            vae=base.vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
        )
        refiner.to("cuda")

        image = base(
            prompt=prompt,
            num_inference_steps=n_steps,
            denoising_end=high_noise_frac,
            output_type="latent",
        ).images
        image = refiner(
            prompt=prompt,
            num_inference_steps=n_steps,
            denoising_start=high_noise_frac,
            image=image,
        ).images[0]
        return image


    ## pass text prompt to music
    def text_to_music(self, text, max_length=1024, top_p=0.9, temperature=1.0):
        tokenizer = AutoTokenizer.from_pretrained('sander-wood/text-to-music')
        model = AutoModelForSeq2SeqLM.from_pretrained('sander-wood/text-to-music')

        input_ids = tokenizer(text,
                              return_tensors='pt',
                              truncation=True,
                              max_length=max_length)['input_ids']

        decoder_start_token_id = model.config.decoder_start_token_id
        eos_token_id = model.config.eos_token_id

        decoder_input_ids = torch.tensor([[decoder_start_token_id]])

        for t_idx in range(max_length):
            outputs = model(input_ids=input_ids,
                            decoder_input_ids=decoder_input_ids)
            probs = outputs.logits[0][-1]
            probs = torch.nn.Softmax(dim=-1)(probs).detach().numpy()
            sampled_id = temperature_sampling(probs=top_p_sampling(probs,
                                                                top_p=top_p,
                                                                return_probs=True),
                                            temperature=temperature)
            decoder_input_ids = torch.cat((decoder_input_ids, torch.tensor([[sampled_id]])), 1)
            if sampled_id!=eos_token_id:
                continue
            else:
                tune = "X:1\n"
                tune += tokenizer.decode(decoder_input_ids[0], skip_special_tokens=True)
                return tune
                break


if __name__ == "__main__":

    # Ejemplo de uso
    assistant = AIAssistant()
    ner_results = assistant.entity_pos_tagger("Nader Jokhadar had given Syria the lead with a well-struck header in the seventh minute.")
    print(ner_results)

    image = assistant.text_to_image_generation("A majestic lion jumping from a big stone at night")
    print(image)

    pos_tags = assistant.grammatical_pos_tagger('Mis amigos están pensando en viajar a Londres este verano')
    print(pos_tags)

    tune = assistant.text_to_music("This is a traditional Irish dance music.")
    print(tune)




from openai import OpenAI
import tiktoken  # Importa tiktoken per contare i token
import json
import ast

# Inizializza il client OpenAI
with open('./AITicket/chiave_api.txt', 'r') as f:
    api_key = f.read().strip()

with open('./AITicket/promptCreazione.txt', 'r') as f:
    prompt = f.read().strip()

client = OpenAI(api_key=api_key)


# Variabili globali per tracciare i token totali
total_input_tokens = 0
total_output_tokens = 0


def creaTicket(messaggio, note):
    print(messaggio, note)
    risposta = creaRisposta(messaggio + "\n\n{alcune note da tenere in conto:}\n" + note)
    try:
        risposta_dict = ast.literal_eval("{" + risposta.split("{", 1)[1].rsplit("}", 1)[0] + "}")
        print(risposta_dict)
    except ValueError as e:
        print("Errore durante la conversione:", e)
    #risposta_dict = json.loads("{" + risposta.split("{", 1)[1].rsplit("}", 1)[0] + "}")
    #print("{" + risposta.split("{", 1)[1].rsplit("}", 1)[0] + "}")
    return risposta_dict




# Calcola il numero di token
def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = len(encoding.encode(text))
    return tokens



# Genera una risposta utilizzando l'API OpenAI
def creaRisposta(input_text):
    global total_input_tokens, total_output_tokens

    input_tokens = count_tokens(input_text)
    total_input_tokens += input_tokens
    
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
        { "role": "system", "content": prompt },
        {
            "role": "user",
            "content": input_text,
        },
    ],
    )

    # Conta i token in output
    output_text = completion.choices[0].message.content
    output_tokens = count_tokens(output_text)
    total_output_tokens += output_tokens

    # Stampa i dettagli sui token
    print(f"Input Tokens: {input_tokens}")
    print(f"Output Tokens: {output_tokens}")
    print(f"Total Input Tokens: {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")

    return output_text

if False:
    print(creaRisposta('''
Buongiorno,

siamo Anna Crema e Riccardo Bidoia, residenti a Cannaregio 566 e Vi scriviamo in quanto siamo in fase di valutazione rifacimento tetto e annessi.
Alleghiamo alla presente il computo metrico redatto dall'architetto incaricato.
Sotto direttive dell'architetto, chiediamo che, attraverso il computo, venga quotato l'intervento, i ponteggi e i parapetti che sono stati predisposti nello stesso.

Vi chiediamo gentilmente di attenervi per quanto possibile alle voci indicate; qualora voleste proporre delle modifiche per il vostro modo di lavorare, Vi invitiamo di indicarle con voci alternative spiegandone i motivi. Le modifiche proposte comunque dovranno mantenere lo stesso grado di prestazione e di sicurezza delle voci di computo.

Vi chiediamo cortesemente di indicare, inoltre, la data di inizio possibile e la durata del lavoro previste.

In attesa di Vostro cortese riscontro restiamo a disposizione per eventuali chiarimenti.

Cordiali saluti,



Anna Crema 3467421587
Riccardo Bidoia 3498843423
    '''))




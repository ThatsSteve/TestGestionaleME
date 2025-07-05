from openai import OpenAI
import tiktoken  # Importa tiktoken per contare i token

import json

# Legge il contenuto del file txt e lo converte in una variabile Python
with open('/home/MEgestionaleTest/MEGestionale/AITicket/fornitori.txt', 'r', encoding='utf-8') as file:
    stringa = file.read()
    fornitori = json.loads(stringa)

fornitoriShort = {}
for i in range(len(fornitori)):
    fornitoriShort[i] = {"Categoria": fornitori[i]["Categoria"],"Specialità": fornitori[i]["Specialità"], "persone" : fornitori[i]["NDipendenti"], "citta": fornitori[i]["citta"]}

# Inizializza il client OpenAI
with open('/home/MEgestionaleTest/MEGestionale/AITicket/chiave_api.txt', 'r') as f:
    api_key = f.read().strip()

with open('/home/MEgestionaleTest/MEGestionale/AITicket/promptfornitori.txt', 'r') as f:
    prompt = f.read().strip()+str(fornitoriShort)
client = OpenAI(api_key=api_key)

# Variabili globali per tracciare i token totali
total_input_tokens = 0
total_output_tokens = 0

# Calcola il numero di token
def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = len(encoding.encode(text))
    return tokens

# Genera una risposta utilizzando l'API OpenAI
def creaRisposta(input_text, precedente=None, correzzioni=None):
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

    return {
        "risposta": output_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens
    }

def getFornitori(lista):
    out = []
    for lavoro in lista:
        fornitori = {}
        for f in lista[lavoro]:
            fornitori[f] = fornitori[f]

        out.append(fornitori)
    return out

def sostituisci_fornitori(dati, fornitori=fornitori):
    risultato = {}
    for categoria, numeri in dati.items():
        # Per ogni categoria, sostituiamo i numeri con i rispettivi fornitori e aggiungiamo l'ID
        fornitori_sostituiti = []
        for numero in numeri:
            if numero < len(fornitori):
                fornitore = fornitori[numero].copy()  # Copia il dizionario per evitare modifiche all'originale
                fornitore["id"] = numero  # Aggiungi l'ID
                fornitori_sostituiti.append(fornitore)
        risultato[categoria] = fornitori_sostituiti
    return risultato

def estraiDaRisposta(risposta):
    try:
        print("AI Response:", risposta)  # Debug: print the entire AI response
        if "<<START>>" not in risposta or "<<END>>" not in risposta:
            print("Delimiters not found in the response!", risposta)  # Extra debug
            raise ValueError("Response missing necessary delimiters.")
        sfornitori = risposta.split("<<START>>")[1]
        sfornitori = sfornitori.split("<<END>>")[0]
        sfornitori = sfornitori.replace("{", "").replace("}", "")
        print("Extracted Suppliers String:", sfornitori)  # Debug: print the extracted suppliers string

        # Identifica se la stringa è un dizionario o una lista di liste
        dati_json = json.loads("{"+sfornitori+"}")
        print("Parsed JSON Data:", dati_json)  # Debug: print the parsed JSON data

        # Se `dati_json` è un dizionario, converte le liste interne e mantiene le chiavi
        if isinstance(dati_json, dict):
            fornitori = {chiave: [int(num) for num in valori] for chiave, valori in dati_json.items()}
        # Se `dati_json` è una lista di liste, converte ogni sottolista in numeri
        elif isinstance(dati_json, list):
            fornitori = [[int(num) for num in sublist] for sublist in dati_json]
        else:
            raise ValueError("Formato non supportato in risposta.")

        riassunto = risposta.split("<<STARTRiassunto>>")[1]
        riassunto = riassunto.split("<<ENDRiassunto>>")[0]
        print("Extracted Summary:", riassunto)  # Debug: print the extracted summary
    except IndexError:
        raise ValueError("Invalid AI response format (IndexError).")
    return [fornitori, riassunto]

def consigliaFornitore(descrizioneLavoro, note, commenti = []):
    input_text = f"descrizione del lavoro: {descrizioneLavoro}\n Note importanti: {note}\n sezione commenti del lavoro: {commenti}."
    # Debug: Log the input text
    print(f"Input Text for OpenAI: {input_text}")
    
    risposta = creaRisposta(input_text)
    rispostaEstratta = estraiDaRisposta(risposta["risposta"])
    # Debug: Log the extracted response
    print(f"Extracted Response: {rispostaEstratta}")
    
    return rispostaEstratta[1], getFornitori(rispostaEstratta[0])
# print(estraiDaRisposta(risposta)[1])
# print(getFornitori(estraiDaRisposta(risposta)[0])

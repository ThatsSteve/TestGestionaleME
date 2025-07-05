from openai import OpenAI
import tiktoken  # Importa tiktoken per contare i token

import json

# Legge il contenuto del file txt e lo converte in una variabile Python
with open('"C:\Users\yscuo\Desktop\V0.2\V0.2\AITicket"/rscan/Desktop/script/py/lavoro/MEGestionale/V0.2/AITicket/contatti.txt', 'r', encoding='utf-8') as file:
    stringa = file.read()
    contatti = json.loads(stringa)

contattiShort = {}
for i in range(len(contatti)):
    contattiShort[i] = {"Categoria": contatti[i]["Categoria"],"Specialità": contatti[i]["Specialità"], "persone" : contatti[i]["NDipendenti"], "citta": contatti[i]["citta"]}
print(contattiShort)
# Inizializza il client OpenAI
with open('"C:\Users\yscuo\Desktop\V0.2\V0.2\AITicket"/rscan/Desktop/script/py/lavoro/MEGestionale/V0.2/AITicket/chiave_api.txt', 'r') as f:
    api_key = f.read().strip()

with open('"C:\Users\yscuo\Desktop\V0.2\V0.2\AITicket"/rscan/Desktop/script/py/lavoro/MEGestionale/V0.2/AITicket/promptContatti.txt', 'r') as f:
    prompt = f.read().strip()+str(contattiShort)
print(prompt)
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
    print(precedente, correzzioni)
    print(input_text)
    global total_input_tokens, total_output_tokens
    if False:
        from time import sleep
        from random import randint
        sleep(0.5)
        return ''' Lavoro richiesto: Sistemazione pavimentazione esterna in asfalto 

Categorie necessarie:
1. Muratore (specializzato in pavimentazioni esterne)
2. Possibile coinvolgimento di un posatore se necessario per la finitura

Ragionamento:
Il lavoro indicato richiede principalmente l'intervento di un muratore specializzato nella sistemazione di pavimentazioni esterne. Dato che non ci sono note molto importanti, si può procedere con la selezione dei contatti più adatti. Essendo Mestre una delle città più vicine all'ubicazione del lavoro (supponiamo che il lavoro abbia luogo a Mestre, per esempio), si preferiranno i contatti situati in questa area per ridurre al minimo la distanza. Non è stato specificato un lavoro di finitura con posatore, ma potrebbe essere considerato se necessario. 

Contatti potenzialmente adatti per 'Sistemazione pavimentazione esterna in asfalto':
- {86} Muratore: Si specializza in posa pavimenti, quindi potrebbe essere utile anche per pavimentazioni esterne.
- {144} Muratore: Si specializza in costruzioni, ristrutturazioni e impiantistica, che può includere lavori di pavimentazione.
- {57} Muratore: Offre servizi generici che potrebbero includere la sistemazione di pavimentazioni.

Conclusione:
Non ci sono contatti che indichino una specializzazione specifica in pavimentazioni esterne in asfalto, ma i contatti scelti offrono servizi che si allineano con il lavoro richiesto. La vicinanza a Mestre è stata considerata per migliorare la logistica del lavoro. 

$% {"Sistemazione pavimentazione esterna in asfalto": ["86", "144", "57"]} $%

^% '''+str(randint(10000,99999))+'''Ho scelto {86} per la sua specializzazione in posa pavimenti, che è rilevante per lavori di pavimentazione. {144} è stato scelto per la sua esperienza in costruzioni e ristrutturazioni, indicando competenza nei lavori edili generici. {57} è stato scelto per le sue capacità in lavori generici, utile per un progetto senza requisiti altamente specializzati. %^
Lavoro richiesto: Sistemazione pavimentazione esterna in asfalto 

Categorie necessarie:
1. Muratore (specializzato in pavimentazioni esterne)
2. Possibile coinvolgimento di un posatore se necessario per la finitura'''
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
        for f in lavoro:
            fornitori[f] = contatti[f]
        
        out.append(fornitori)
    return out
        


def sostituisci_contatti(dati, contatti=contatti):
    print(dati)
    risultato = {}
    for categoria, numeri in dati.items():
        # Per ogni categoria, sostituiamo i numeri con i rispettivi contatti e aggiungiamo l'ID
        contatti_sostituiti = []
        for numero in numeri:
            if numero < len(contatti):
                contatto = contatti[numero].copy()  # Copia il dizionario per evitare modifiche all'originale
                contatto["id"] = numero  # Aggiungi l'ID
                contatti_sostituiti.append(contatto)
        risultato[categoria] = contatti_sostituiti
    return risultato


def estraiDaRisposta(risposta):
    print(risposta)
    sContatti = risposta.split("$%")[1]
    sContatti = sContatti.split("%$")[0]
    sContatti = sContatti.replace("{", "").replace("}", "")
    print(sContatti)
    
    # Identifica se la stringa è un dizionario o una lista di liste
    dati_json = json.loads("{"+sContatti+"}")
    
    # Se `dati_json` è un dizionario, converte le liste interne e mantiene le chiavi
    if isinstance(dati_json, dict):
        contatti = {chiave: [int(num) for num in valori] for chiave, valori in dati_json.items()}
    # Se `dati_json` è una lista di liste, converte ogni sottolista in numeri
    elif isinstance(dati_json, list):
        contatti = [[int(num) for num in sublist] for sublist in dati_json]
    else:
        raise ValueError("Formato non supportato in risposta.")
    
    riassunto = risposta.split("^%")[1]
    riassunto = riassunto.split("%^")[0]
    return [contatti, riassunto]



# risposta = '''
# **Lista dei lavori necessari e categorie:**
# 
# 1. Rifacimento tetto - Categoria: Muratore
# 2. Installazione ponteggi - Categoria: Ponteggi
# 3. Realizzazione parapetti - Categoria: Carpentiere
# 
# **Ragionamento:**
# 
# 1. **Rifacimento tetto:** Dato che Cannaregio si trova a Venezia, la vicinanza a Venezia e la specialità nel rifacimento di tetti costituirà il criterio principale nella selezione dei contatti da considerare come priorità. Verranno quindi presi in considerazione contatti che hanno come specialità il rifacimento di tetti o che operano principalmente a Venezia o nelle vicinanze.
# 
# 2. **Installazione ponteggi:** Dare priorità ai contatti con la specialità nei ponteggi, in particolare, coloro che lavorano a Venezia o nelle vicinanze per ridurre costi di trasporto e facilitare la gestione logistica.
# 
# 3. **Realizzazione parapetti:** Selezionare carpentieri con specialità nella realizzazione di parapetti o che siano situati a Venezia per agevolare l'esecuzione del lavoro e la gestione pratica in loco.
# 
# **Conclusione:**
# 
# $%[
# ["6", "9", "12"],
# ["29"],
# ["32", "34", "33"]
# ]$%
# 
# ^%
# Per il rifacimento del tetto, i contatti scelti sono il numero 6 (Codevigo Padova) che ha esperienza nel rifacimento di tetti, il numero 9 (Mestre) con specialità in isolamenti e cappotti, e il numero 12 (Venezia) specializzato in grossi restauri, considerando anche la vicinanza a Venezia. 
# 
# Per l'installazione dei ponteggi, il contatto scelto è il numero 29, specializzato in ponteggi a Venezia.
# 
# Per la realizzazione dei parapetti, sono stati scelti il numero 32 (Udine) specializzato in ringhiere e parapetti, il 34 (Marghera) e il 33 (Treviso) con specialità in carpentiere, per le loro localizzazioni limitrofe a Venezia in modo da facilitare i lavori in loco.
# ^%
# 
#
# risposta = creaRisposta('''
# Buongiorno,
# 
# siamo Anna Crema e Riccardo Bidoia, residenti a Cannaregio 566 e Vi scriviamo in quanto siamo in fase di valutazione rifacimento tetto e annessi.
# Alleghiamo alla presente il computo metrico redatto dall'architetto incaricato.
# Sotto direttive dell'architetto, chiediamo che, attraverso il computo, venga quotato l'intervento, i ponteggi e i parapetti che sono stati predisposti nello stesso.
# 
# Vi chiediamo gentilmente di attenervi per quanto possibile alle voci indicate; qualora voleste proporre delle modifiche per il vostro modo di lavorare, Vi invitiamo di indicarle con voci alternative spiegandone i motivi. Le modifiche proposte comunque dovranno mantenere lo stesso grado di prestazione e di sicurezza delle voci di computo.
# 
# Vi chiediamo cortesemente di indicare, inoltre, la data di inizio possibile e la durata del lavoro previste.
# 
# In attesa di Vostro cortese riscontro restiamo a disposizione per eventuali chiarimenti.
# 
# Cordiali saluti,
# 
# 
# 
# Anna Crema 3467421587
# Riccardo Bidoia 3498843423
# ''')
# 
# risposta = creaRisposta('''
# SEGNALAZIONE ORIGINALE
#  	Infiltrazione:
# Buongiorno,
# la sig.ra D'Agostino ci segnala che nel suo magazzino ed al muro esterno ci sono dei danni dovuti ad una probabile infiltrazione dal piano superiore ( sopra abitano il sig. Mazzolato civ.2 e il sig. Di Santo civ.4), in allegato le foto.
# Grazie,
# cordiali saluti.
# 
# ''')
# print(estraiDaRisposta(risposta)[1])
# print(getFornitori(estraiDaRisposta(risposta)[0]))
#


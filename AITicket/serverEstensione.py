from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
from odf.opendocument import load as load_odt
from odf.text import P
from scegliFornitore import creaRisposta, estraiDaRisposta, sostituisci_contatti  # Importa la funzione creaRisposta dal modulo
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Assicurati che la directory 'upload' esista
UPLOAD_FOLDER = './upload'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def read_pdf(file_path):
    """Funzione per leggere il contenuto di un file PDF."""
    text = ""
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def read_odt(file_path):
    """Funzione per leggere il contenuto di un file ODT."""
    text = ""
    odt_file = load_odt(file_path)
    for element in odt_file.getElementsByType(P):
        text += ''.join(node.data for node in element.childNodes if node.nodeType == node.TEXT_NODE) + "\n"
    return text

@app.route('/api/consiglia_fornitori', methods=['POST'])
def consiglia_fornitori():
    # Ottieni i dati JSON e le note dal form-data
    dati = json.loads(request.form.get('dati'))
    note = request.form.get('note')
    correzioni = request.form.get('correzioni')
    RispostaOld = request.form.get('RispostaOld')
    contattiOld = request.form.get('contattiOld')

    print("Dati ricevuti:", dati)
    print("Note aggiuntive:", note)
    if correzioni and RispostaOld and contattiOld:
        testo_completo = f'''Il titolo della pratica è: "{dati["Titolo"]}"
precedentemente avevi scelto i contatti: {contattiOld}
col seguente ragionamento: {RispostaOld}
ma l'utente ha suggerito delle cose da cambiare con la seguente richiesta: {correzioni}'''
    else:
    # Testo combinato da inviare a creaRisposta
        testo_completo = f'''Questa richiesta è stata generata dal gestionale, il titolo della pratica è: "{dati["Titolo"]}"
Le note dell'operatore MOLTO IMPORTANTI HANNO LA PRECEDENZA (se presenti): "{note}"'''

    # Gestisci l'allegato se presente
    if 'allegato' in request.files:
        file = request.files['allegato']
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        print(f"File '{file.filename}' salvato in {file_path}")
        
        # Estrai e aggiungi il contenuto in base al tipo di file
        if file.filename.lower().endswith('.pdf'):
            file_content = read_pdf(file_path)
        elif file.filename.lower().endswith('.odt'):
            file_content = read_odt(file_path)
        else:
            file_content = "Formato file non supportato."
        
        print("Contenuto del file:\n", file_content)
        testo_completo += "\nè inoltre stato caricato un allegato col seguente testo:\n" + file_content  # Aggiungi il testo dell'allegato ai dati
    else:
        print("Nessun allegato ricevuto.")
    
    # Invia il testo completo (dati + contenuto del file se presente) a creaRisposta
    risposta = creaRisposta(testo_completo)
    print("Risposta elaborata:\n", risposta)    
    # Invia il testo completo (dati + contenuto del file se presente) a creaRisposta
    datiEstratti = estraiDaRisposta(risposta)
    print("\n\nRisposta:\n", datiEstratti)
    contatti = sostituisci_contatti(datiEstratti[0])
    #print(sostituisci_contatti(datiEstratti[0]))
    # Risposta di successo con il risultato di creaRisposta
    return jsonify({"message": "Dati ricevuti con successo", "risposta": datiEstratti[1], "contatti": contatti}), 200

if __name__ == '__main__':
    app.run(port=5100)

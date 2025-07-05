from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Cliente, Fornitore, Categoria, Lavoro, Comment, Contatti, Riferimento, LavoroFornitore, EmailAddress, CronologiaModifiche
from django.core.files.storage import default_storage
from django.utils.timezone import now
import os
import json
from django.http import FileResponse
from django.conf import settings
from django.db.models import F  # Importa F per operazioni sui campi del database
from django.views.decorators.clickjacking import xframe_options_exempt # Added import
from openai import OpenAI
import tiktoken  # Importa tiktoken per contare i token
import django
import time  # Import time module for measuring time
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from AITicket.creaTicket import creaTicket

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate
import base64
import uuid
import requests
from urllib.parse import unquote
import os
from pathlib import Path

pc = "server"

def create_ticket_if(request):
    return render(request, 'iframe/createticket_if.html')


def aggiungi_cliente(request):
    return render(request, 'aggiungi_cliente.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')  # Redirect to a success page.
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to a login page.

@login_required
def index(request):
    return render(request, 'index.html')

def strumenti_ai_view(request):
    return render(request, 'strumentiAI.html')

def fornitori_view(request):
    return render(request, 'fornitori.html')

def clienti_view(request):
    return render(request, 'clienti.html')

import mimetypes

def serve_uploaded_file_query(request):
    filename = request.GET.get('file')
    if not filename:
        return JsonResponse({'status': 'error', 'message': 'Nome del file non fornito.'}, status=400)

    try:
        # Prepara il percorso completo del file
        file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', filename)
        if (os.path.exists(file_path)):
            # Determina il content type del file
            mime_type, _ = mimetypes.guess_type(file_path)
            content_type = mime_type if mime_type else "application/octet-stream"

            return FileResponse(open(file_path, 'rb'), as_attachment=False, content_type=content_type)
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        return JsonResponse({'status': 'error', 'message': 'File non trovato.'}, status=404)



@csrf_exempt
def create_ticket(request):
    if (request.method == 'POST'):
        try:
            # Parse JSON data from the request
            data = json.loads(request.body)
            message = data.get('message')
            notes = data.get('notes')
            
            # Genera il ticket usando creaTicket
            ticket = creaTicket(message, notes)
            print("Ticket generato:", ticket)  # Debug: stampa il contenuto del ticket
            
            # Salva il ticket nel database
            new_ticket = Lavoro.objects.create(
                descrizione=ticket.get('titolo', ''),
                note=ticket.get('note', ''),
                position= 0,
                importo=0,  # O qualsiasi valore predefinito, se necessario
                fase='in_sospeso_per_valutazioni'  # O imposta la fase appropriata
            )
            
            new_comment = Comment.objects.create(
                work_id=data['work_id'],
                content=data['content'],
                timestamp=now(),
                attachment=data.get('attachment')
            )
            
            # Rispondi con un messaggio di successo e l'ID del nuovo ticket
            return JsonResponse({'status': 'success', 'message': 'Ticket creato con successo', 'ticket_id': new_ticket.id})
        
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            # Debug: stampa il messaggio di errore completo
            print("Errore durante la creazione del ticket:", str(e))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)


import uuid  # Import uuid for generating unique identifiers

@csrf_exempt
def upload_attachment(request):
    if (request.method == 'POST' and request.FILES.get('file')):
        try:
            file = request.FILES['file']
            # Generate a unique identifier and append it to the filename if a file with the same name exists
            path = os.path.join('uploads', file.name)
            if default_storage.exists(path):
                unique_id = uuid.uuid4().hex[:4]  # Use the first 4 characters of the UUID
                filename, extension = os.path.splitext(file.name)
                path = os.path.join('uploads', f"{filename}_{unique_id}{extension}")
            
            filename = default_storage.save(path, file)
            
            # Get the relative path for the URL
            file_url = f"upload/?file={os.path.basename(filename)}"
            return JsonResponse({'status': 'success', 'message': 'File caricato con successo.', 'file_url': file_url})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Nessun file caricato.'}, status=400)


def get_stage_name(stage, request=None):
    stage_names = {
        "in_sospeso_per_valutazioni": "In sospeso per valutazioni",
        "nuovo_sopralluogo": "Nuovo sopralluogo",
        "da_preventivare": "Da preventivare",
        "inviato_preventivo": "Inviato preventivo",
        "confermato_da_eseguire": "Confermato da eseguire",
        "in_corso": "In corso",
        "da_fatturare": "Da fatturare",
        "fatturate_da_pagare": "Fatturate da pagare",
        "archiviate": "Archiviate",
        "offerte_perse": "Offerte Perse",
        "con_piattaforma_o_fune": "In corso o In Lavorazione"  # Updated name
    }
    
    # Se è disponibile la request, usa i nomi personalizzati dalla sessione
    if request and hasattr(request, 'session'):
        custom_names = request.session.get('custom_stage_names', {})
        stage_names.update(custom_names)
    
    return stage_names.get(stage, "Sconosciuto")


def get_work_stages(request):
    start_time = time.time()
    stages = {
        "in_sospeso_per_valutazioni": {'items': [], 'totalValue': 0},
        "nuovo_sopralluogo": {'items': [], 'totalValue': 0},
        "da_preventivare": {'items': [], 'totalValue': 0},
        "inviato_preventivo": {'items': [], 'totalValue': 0},
        "confermato_da_eseguire": {'items': [], 'totalValue': 0},
        "in_corso": {'items': [], 'totalValue': 0},
        "da_fatturare": {'items': [], 'totalValue': 0},
        "fatturate_da_pagare": {'items': [], 'totalValue': 0},
        "archiviate": {'items': [], 'totalValue': 0},
        "offerte_perse": {'items': [], 'totalValue': 0},
        "con_piattaforma_o_fune": {'items': [], 'totalValue': 0}
    }

    # Carica tutti i lavori con le relazioni in una singola query
    lavori = (Lavoro.objects
              .select_related('cliente', 'riferimento')  # Carica cliente e riferimento
              .prefetch_related('lavoro_fornitori__fornitore')  # Carica fornitori
              .order_by('position'))

    # Processo batch per i lavori
    for lavoro in lavori:
        # Prepara i dati dei fornitori una volta sola
        fornitori_list = [
            lf.fornitore.descrizione 
            for lf in lavoro.lavoro_fornitori.all()
        ]

        item = {
            'id': lavoro.id,
            'title': lavoro.descrizione,
            'client': lavoro.cliente.descrizione if lavoro.cliente else 'Cliente sconosciuto',
            'client_address': lavoro.cliente.indirizzo if lavoro.cliente else '',
            'riferimento': (f"{lavoro.riferimento.nome} {lavoro.riferimento.cognome}" 
                          if lavoro.riferimento else None),
            'value': lavoro.importo or 0,
            'date': lavoro.data_creazione.strftime('%d %B %Y'),
            'position': lavoro.position,
            'note': lavoro.note,
            'fornitori': fornitori_list,
            'selezionato': lavoro.selezionato  # Add the 'selezionato' field
        }

        if lavoro.fase in stages:
            stages[lavoro.fase]['items'].append(item)
            stages[lavoro.fase]['totalValue'] += item['value']

    #print(f"Total execution time: {time.time() - start_time} seconds")
    return JsonResponse(stages)


def get_clients(request):
    clients = Cliente.objects.all()
    clients_data = [{'id': client.id, 'descrizione': client.descrizione, 'societa': client.societa} for client in clients]
    return JsonResponse(clients_data, safe=False)


def get_suppliers(request):
    suppliers = Fornitore.objects.all()
    suppliers_data = [{'id': supplier.id, 'nome': supplier.descrizione} for supplier in suppliers]
    return JsonResponse(suppliers_data, safe=False)


def lista_contatti(request):
    fornitori = Fornitore.objects.all()
    fornitori_data = [{
        "id": fornitore.id,
        "Nome": fornitore.descrizione,
        "Cognome": fornitore.cognome,
        "NDipendenti": fornitore.numero_dipendenti,
        "Telefono": fornitore.cellulari,
        "Sito": fornitore.sito_web,
        "Creato": fornitore.created_at.strftime('%d/%m/%Y') if (hasattr(fornitore, 'created_at') and fornitore.created_at) else '',
        "Email": fornitore.email,
        "Categoria": fornitore.categoria.nome if fornitore.categoria else '',
        "PIVA": fornitore.partita_iva,
        "Specialità": fornitore.specialita,
        "Citta": fornitore.luogo,
        "Note": fornitore.note,
        "CodiceFiscale": fornitore.codice_fiscale,
        "Affidabilita": fornitore.affidabilita,
    } for fornitore in fornitori]


    return JsonResponse(fornitori_data, safe=False)

def lista_clienti(request):
    clienti = Cliente.objects.all()
    clienti_data = [{
        "id": cliente.id,
        "descrizione": cliente.descrizione,
        "cognome": cliente.cognome,
        "cellulare": cliente.cellulare,
        "email": cliente.email,
        "indirizzo": cliente.indirizzo,
        "nome": cliente.nome,
        "codice_fiscale": cliente.codice_fiscale,
        "piva": cliente.piva,
    } for cliente in clienti]

    return JsonResponse(clienti_data, safe=False)

@csrf_exempt
def add_work(request):
    if (request.method == 'POST'):
        data = json.loads(request.body)
        try:
            # Incrementa la posizione di tutti i lavori esistenti nella stessa fase
            Lavoro.objects.filter(fase=data.get('fase', 'in_sospeso_per_valutazioni')).update(position=F('position') + 1)

            # Crea il nuovo lavoro
            new_work = Lavoro.objects.create(
                descrizione=data['descrizione'],
                fase=data.get('fase', 'in_sospeso_per_valutazioni'),
                importo=data.get('importo', 0),
                note=data.get('note', ''),
                cliente_id=data.get('cliente_id'),
                position=data.get('position', 0),
                riferimento_id=data.get('riferimento_id')  # Invia l'ID del riferimento
            )
            for fornitore_id in data.get('fornitore_ids', []):
                LavoroFornitore.objects.create(lavoro=new_work, fornitore_id=fornitore_id)
            
            # Salva cronologia
            salva_cronologia(
                'work', 
                'create', 
                f"Nuovo ticket #{new_work.id} creato: '{new_work.descrizione}' - Fase: {new_work.fase} - Importo: {new_work.importo}", 
                new_work.id
            )
            
            return JsonResponse({'status': 'success', 'message': 'Lavoro aggiunto con successo.', 'work_id': new_work.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)





@csrf_exempt
def update_work_stage(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)

            # Verifica che `data` sia una lista
            if (not isinstance(data, list)):
                return JsonResponse({'status': 'error', 'message': 'Formato dei dati non valido, ci si aspetta una lista.'}, status=400)

            # Itera su ciascuna colonna ricevuta (ad esempio source e destination)
            for column in data:
                stage = column.get('stage')
                items = column.get('items')

                # Verifica se `stage` e `items` sono validi
                if (stage is None or not isinstance(items, list)):
                    return JsonResponse({'status': 'error', 'message': 'Formato dei dati non valido per una colonna.'}, status=400)

                # Aggiorna i lavori nella fase specificata
                for item in items:
                    lavoro_id = item.get('id')
                    position = item.get('position')

                    if (lavoro_id is None or position is None):
                        return JsonResponse({'status': 'error', 'message': 'ID del lavoro o posizione non forniti.'}, status=400)

                    try:
                        lavoro = Lavoro.objects.get(id=lavoro_id)
                        old_stage = lavoro.fase  # Save the old stage
                        lavoro.position = position  # Aggiorna la posizione
                        lavoro.fase = stage  # Aggiorna la fase
                        lavoro.save()

                        # Add a system comment about the stage change if the stage has changed
                        if old_stage != stage:
                            Comment.objects.create(
                                work_id=lavoro_id,
                                content=f"|system|{{Fase modificata da {get_stage_name(old_stage, request)} a {get_stage_name(stage, request)}}}",
                                timestamp=now()
                            )
                            # Salva cronologia
                            salva_cronologia(
                                'work', 
                                'move', 
                                f"Ticket #{lavoro.id} spostato da '{get_stage_name(old_stage, request)}' a '{get_stage_name(stage, request)}'", 
                                lavoro.id
                            )
                    except Lavoro.DoesNotExist:
                        return JsonResponse({'status': 'error', 'message': f'Lavoro con ID {lavoro_id} non trovato.'}, status=404)

            return JsonResponse({'status': 'success', 'message': 'Fasi dei lavori aggiornate con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)
    
    
    


@csrf_exempt
def delete_work(request):
    if (request.method == 'POST'):
        data = json.loads(request.body)
        work_id = data.get('id')
        try:
            lavoro = Lavoro.objects.get(id=work_id)
            # Salva cronologia prima di eliminare
            salva_cronologia(
                'work', 
                'delete', 
                f"Ticket #{lavoro.id} eliminato: '{lavoro.descrizione}' - Fase: {lavoro.fase}", 
                lavoro.id
            )
            lavoro.delete()
            return JsonResponse({'status': 'success', 'message': 'Lavoro eliminato con successo.'})
        except Lavoro.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lavoro non trovato'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)






def get_comments(request):
    work_id = request.GET.get('work_id')
    comments = Comment.objects.filter(work_id=work_id).all()
    comments_data = []

    for comment in comments:
        attachment_url = None
        if (comment.attachment):
            # Prepara il percorso completo del file
            attachment_url = f"{comment.attachment}"
        
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'timestamp': comment.timestamp.strftime('%d %B %Y, %H:%M'),
            'attachment': attachment_url
        })

    return JsonResponse({'comments': comments_data})



@csrf_exempt
def add_comment(request):
    if (request.method == 'POST'):
        data = json.loads(request.body)
        try:
            new_comment = Comment.objects.create(
                work_id=data['work_id'],
                content=data['content'],
                timestamp=now(),
                attachment=data.get('attachment')
            )
            return JsonResponse({'status': 'success', 'message': 'Commento aggiunto con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

def update_work_iframe(request, work_id):
    work = get_object_or_404(Lavoro, id=work_id)
    fornitori = work.lavoro_fornitori.all()
    fornitori_data = [{'id': lf.fornitore.id, 'descrizione': lf.fornitore.descrizione, 'confermato': lf.confermato} for lf in fornitori]
    work_data = {
        "id": work.id,
        "descrizione": work.descrizione,
        "importo": work.importo,
        "fase": work.fase,
        "note": work.note,
        "cliente_id": work.cliente_id,
        "riferimento_id": work.riferimento_id,
        "fornitori": fornitori_data
    }
    print(json.dumps(work_data))

    return render(request, 'iframe/update_work_iframe.html', {'work_json': json.dumps(work_data)})




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def update_work(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            work_id = data.get('id')  # Ensure the ID is passed
            if not work_id:
                return JsonResponse({'status': 'error', 'message': 'ID del lavoro mancante'}, status=400)

            work = get_object_or_404(Lavoro, id=work_id)

            # Se stiamo solo aggiornando il campo selezionato, non tocchiamo gli altri campi
            if len(data.keys()) == 2 and 'id' in data and 'selezionato' in data:
                old_value = work.selezionato
                work.selezionato = data['selezionato']
                work.save()
                # Salva cronologia
                salva_cronologia(
                    'work', 
                    'update', 
                    f"Ticket #{work.id} - Selezione cambiata da {old_value} a {data['selezionato']}", 
                    work.id
                )
                return JsonResponse({'status': 'success'})

            # Altrimenti procediamo con l'aggiornamento completo
            old_descrizione = work.descrizione
            old_importo = work.importo
            old_fase = work.fase
            old_note = work.note
            
            work.descrizione = data.get('descrizione', work.descrizione)
            work.importo = data.get('importo', work.importo)
            work.fase = data.get('fase', work.fase)
            work.note = data.get('note', work.note)
            work.selezionato = data.get('selezionato', work.selezionato)  # Update the 'selezionato' field
            work.save()
            
            # Salva cronologia delle modifiche
            modifiche = []
            if old_descrizione != work.descrizione:
                modifiche.append(f"Descrizione: '{old_descrizione}' → '{work.descrizione}'")
            if old_importo != work.importo:
                modifiche.append(f"Importo: {old_importo} → {work.importo}")
            if old_fase != work.fase:
                modifiche.append(f"Fase: '{old_fase}' → '{work.fase}'")
            if old_note != work.note:
                modifiche.append(f"Note modificate")
            
            if modifiche:
                salva_cronologia(
                    'work', 
                    'update', 
                    f"Ticket #{work.id} - {', '.join(modifiche)}", 
                    work.id
                )

            # Update suppliers only if they are provided in the data
            if 'fornitori' in data:
                LavoroFornitore.objects.filter(lavoro=work).delete()
                for fornitore in data['fornitori']:
                    LavoroFornitore.objects.create(
                        lavoro=work, 
                        fornitore_id=fornitore['id'], 
                        confermato=fornitore.get('confermato', False)  # Save the "confermato" status
                    )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)





def get_work(request, work_id):
    work = get_object_or_404(Lavoro, id=work_id)
    fornitori = work.lavoro_fornitori.all()
    fornitori_data = [{'id': lf.fornitore.id, 'descrizione': lf.fornitore.descrizione, 'confermato': lf.confermato} for lf in fornitori]
    return JsonResponse({
        'title': work.descrizione,
        'client': work.cliente.descrizione if work.cliente else '',
        'value': work.importo,
        'fornitori': fornitori_data,
        'notes': work.note
    })

@xframe_options_exempt # Added view function
def aggiungi_fornitore(request):
    return render(request, 'iframe/aggiungi_fornitore.html')

@xframe_options_exempt
def consiglia_fornitori_iframe(request):
    return render(request, 'iframe/consiglia_fornitori.html')

@csrf_exempt
def add_cliente(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            new_cliente = Cliente.objects.create(
                nome=data.get('nome'),
                cognome=data.get('cognome'),
                email=data.get('email'),
                cellulare=data.get('cellulare'),
                indirizzo=data.get('indirizzo', ''),
                descrizione=data.get('descrizione', ''),
                societa=data.get('societa', False),
                piva=data.get('piva', ''),
                codice_fiscale=data.get('codice_fiscale', '')
            )
            return JsonResponse({'status': 'success', 'message': 'Cliente aggiunto con successo.', 'cliente_id': new_cliente.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)



def get_client_details(request, id):
    """
    Recupera i dettagli di un cliente dato il suo ID.
    """
    try:
        # Recupera il cliente con l'ID fornito
        cliente = get_object_or_404(Cliente, id=id)
        
        # Costruisce il dizionario con i dettagli del cliente
        cliente_data = {
            'id': cliente.id,
            'nome': cliente.nome,
            'cognome': cliente.cognome,
            'email': cliente.email,
            'cellulare': cliente.cellulare,
            'indirizzo': cliente.indirizzo,
            'descrizione': cliente.descrizione,
            'societa': cliente.societa,
            'piva': cliente.piva,
            'codice_fiscale': cliente.codice_fiscale,
        }
        
        # Restituisce i dettagli come JSON
        return JsonResponse(cliente_data, safe=False)
    except Exception as e:
        # In caso di errore, restituisce una risposta con errore
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_fornitore_details(request, id):
    try:
        # Recupera il fornitore con l'ID fornito
        fornitore = get_object_or_404(Fornitore, id=id)
        
        # Costruisce il dizionario con i dettagli del fornitore
        fornitore_data = {
            'id': fornitore.id,
            'descrizione': fornitore.descrizione,
            'cellulari': fornitore.cellulari,
            'numero_dipendenti': fornitore.numero_dipendenti,
            'sito_web': fornitore.sito_web,
            'email': fornitore.email,
            'partita_iva': fornitore.partita_iva,
            'specialita': fornitore.specialita,
            'luogo': fornitore.luogo,
            'note': fornitore.note,
            'categoria': fornitore.categoria.nome if fornitore.categoria else None,
            'codice_fiscale': fornitore.codice_fiscale,
            'affidabilita': fornitore.affidabilita
        }
        
        # Restituisce i dettagli come JSON
        return JsonResponse(fornitore_data, safe=False)
    except Exception as e:
        # In caso di errore, restituisce una risposta con errore
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def add_fornitore(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            fornitore = Fornitore.objects.create(
                descrizione=data.get('descrizione'),
                nome=data.get('nome'),
                cognome=data.get('cognome'),
                attivita=data.get('attivita'),
                cellulari=data.get('cellulari'),
                numero_dipendenti=data.get('numero_dipendenti'),
                sito_web=data.get('sito_web'),
                email=data.get('email'),
                partita_iva=data.get('partita_iva'),
                specialita=data.get('specialita'),
                luogo=data.get('luogo'),
                note=data.get('note'),
                categoria_id=data.get('categoria_id'),
                codice_fiscale=data.get('codice_fiscale'),
                affidabilita=data.get('affidabilita')
            )
            return JsonResponse({'status': 'success', 'fornitore_id': fornitore.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})





def list_categorie(request):
    if (request.method == 'GET'):
        categorie = Categoria.objects.all()
        categorie_data = [{"id": categoria.id, "nome": categoria.nome} for categoria in categorie]
        return JsonResponse({"status": "success", "categorie": categorie_data})
    return JsonResponse({"status": "error", "message": "Metodo non supportato"})



@csrf_exempt
def add_categoria(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            nome = data.get('nome')
            if (not nome):
                return JsonResponse({"status": "error", "message": "La nome è obbligatoria"})
            
            categoria = Categoria.objects.create(nome=nome)
            return JsonResponse({"status": "success", "categoria": {"id": categoria.id, "nome": categoria.nome}})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Metodo non supportato"})


@csrf_exempt
def delete_comment(request):
    if (request.method == 'POST'):
        try:
            # Parse the JSON body of the request
            data = json.loads(request.body)
            comment_id = data.get('comment_id')

            if (not comment_id):
                return JsonResponse({'status': 'error', 'message': 'ID del commento non fornito.'}, status=400)

            # Get the comment object and delete it
            comment = get_object_or_404(Comment, id=comment_id)
            comment.delete()

            return JsonResponse({'status': 'success', 'message': 'Commento eliminato con successo.'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'JSON non valido.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Metodo non consentito.'}, status=405)

@csrf_exempt
def add_riferimento(request):
    if (request.method == 'POST'):
        try:
            data = json.loads(request.body)
            riferimento = Riferimento.objects.create(
                nome=data.get('nome'),
                cognome=data.get('cognome'),
                telefono=data.get('telefono'),
                email=data.get('email')
            )
            return JsonResponse({'status': 'success', 'riferimento_id': riferimento.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

def get_riferimenti(request):
    riferimenti = Riferimento.objects.all()
    riferimenti_data = [{'id': riferimento.id, 'nome': riferimento.nome, 'cognome': riferimento.cognome, 'telefono': riferimento.telefono, 'email': riferimento.email} for riferimento in riferimenti]
    return JsonResponse(riferimenti_data, safe=False)

def get_riferimento_details(request, id):
    try:
        riferimento = get_object_or_404(Riferimento, id=id)
        riferimento_data = {
            'id': riferimento.id,
            'nome': riferimento.nome,
            'cognome': riferimento.cognome,
            'telefono': riferimento.telefono,
            'email': riferimento.email
        }
        return JsonResponse(riferimento_data, safe=False)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def update_fornitore(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fornitore = get_object_or_404(Fornitore, id=id)
            fornitore.descrizione = data.get('descrizione', fornitore.descrizione)
            fornitore.nome = data.get('nome', fornitore.nome)
            fornitore.cognome = data.get('cognome', fornitore.cognome)
            fornitore.attivita = data.get('attivita', fornitore.attivita)
            fornitore.cellulari = data.get('cellulari', fornitore.cellulari)
            fornitore.numero_dipendenti = data.get('numero_dipendenti', fornitore.numero_dipendenti)
            fornitore.sito_web = data.get('sito_web', fornitore.sito_web)
            fornitore.email = data.get('email', fornitore.email)
            fornitore.partita_iva = data.get('partita_iva', fornitore.partita_iva)
            fornitore.specialita = data.get('specialita', fornitore.specialita)
            fornitore.luogo = data.get('luogo', fornitore.luogo)
            fornitore.note = data.get('note', fornitore.note)
            fornitore.categoria_id = data.get('categoria_id', fornitore.categoria_id)
            fornitore.codice_fiscale = data.get('codice_fiscale', fornitore.codice_fiscale)
            fornitore.affidabilita = data.get('affidabilita', fornitore.affidabilita)
            fornitore.save()
            return JsonResponse({'status': 'success', 'message': 'Fornitore aggiornato con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

@csrf_exempt
def delete_fornitore(request, id):
    if request.method == 'POST':
        try:
            fornitore = get_object_or_404(Fornitore, id=id)
            fornitore.delete()
            return JsonResponse({'status': 'success', 'message': 'Fornitore eliminato con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

@xframe_options_exempt
def update_fornitore_iframe(request, id):
    fornitore = get_object_or_404(Fornitore, id=id)
    fornitore_data = {
        'id': fornitore.id,
        'descrizione': fornitore.descrizione,
        'nome': fornitore.nome,
        'cognome': fornitore.cognome,
        'attivita': fornitore.attivita,
        'cellulari': fornitore.cellulari,
        'numero_dipendenti': fornitore.numero_dipendenti,
        'sito_web': fornitore.sito_web,
        'email': fornitore.email,
        'partita_iva': fornitore.partita_iva,
        'specialita': fornitore.specialita,
        'luogo': fornitore.luogo,
        'note': fornitore.note,
        'categoria_id': fornitore.categoria_id,
        'codice_fiscale': fornitore.codice_fiscale,
        'affidabilita': fornitore.affidabilita,
    }
    return render(request, 'iframe/update_fornitore.html', {'fornitore_json': json.dumps(fornitore_data)})

@csrf_exempt
def update_cliente(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cliente = get_object_or_404(Cliente, id=id)
            cliente.nome = data.get('nome', cliente.nome)
            cliente.cognome = data.get('cognome', cliente.cognome)
            cliente.email = data.get('email', cliente.email)
            cliente.cellulare = data.get('cellulare', cliente.cellulare)
            cliente.indirizzo = data.get('indirizzo', cliente.indirizzo)
            cliente.descrizione = data.get('descrizione', cliente.descrizione)
            cliente.societa = data.get('societa', cliente.societa)
            cliente.piva = data.get('piva', cliente.piva)
            cliente.codice_fiscale = data.get('codice_fiscale', cliente.codice_fiscale)
            cliente.save()
            return JsonResponse({'status': 'success', 'message': 'Cliente aggiornato con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

@csrf_exempt
def delete_cliente(request, id):
    if request.method == 'POST':
        try:
            cliente = get_object_or_404(Cliente, id=id)
            cliente.delete()
            return JsonResponse({'status': 'success', 'message': 'Cliente eliminato con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

@xframe_options_exempt
def update_cliente_iframe(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente_data = {
        'id': cliente.id,
        'nome': cliente.nome,
        'cognome': cliente.cognome,
        'email': cliente.email,
        'cellulare': cliente.cellulare,
        'indirizzo': cliente.indirizzo,
        'descrizione': cliente.descrizione,
        'societa': cliente.societa,
        'piva': cliente.piva,
        'codice_fiscale': cliente.codice_fiscale,
    }
    return render(request, 'iframe/update_cliente.html', {'cliente_json': json.dumps(cliente_data)})

from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def consiglia_fornitori(request):
    try:
        data = json.loads(request.body)
        work_id = data.get('work_id', '')
        note = data.get('note', '')  # Ottieni le note dal corpo della richiesta JSON
        if not work_id:
            return JsonResponse({'status': 'error', 'message': 'Work ID is required'}, status=400)

        work = get_object_or_404(Lavoro, id=work_id)
        input_text = work.descrizione

        # Debug: Log the input text and note
        print(f"Input Text: {input_text}")
        print(f"Note: {note}")

        riassunto, fornitori = consigliaFornitore(input_text, note)

        # Debug: Log the response from consigliaFornitore
        print(f"Riassunto: {riassunto}")
        print(f"Fornitori: {fornitori}")

        return JsonResponse({
            'status': 'success',
            'riassunto': riassunto,
            'fornitori': fornitori
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Lavoro.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Work not found'}, status=404)
    except Exception as e:
        # Debug: Log the exception
        print(f"Exception: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def aggiungi_fornitori(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("Dati ricevuti:", data)  # Debug: stampa i dati ricevuti
            work_id = data.get('work_id')
            fornitori_ids = data.get('fornitori_ids', [])
            print("Work ID:", work_id)  # Debug: stampa il work_id
            print("Fornitori IDs:", fornitori_ids)  # Debug: stampa i fornitori_ids

            if not work_id:
                return JsonResponse({'status': 'error', 'message': 'Work ID è richiesto'}, status=400)

            if fornitori_ids == []:
                return JsonResponse({'status': 'success', 'message': 'Nessun fornitore aggiunto'})

            work = get_object_or_404(Lavoro, id=work_id)
            print("Lavoro trovato:", work)  # Debug: stampa il lavoro trovato

            for fornitore_id in fornitori_ids:
                print("Aggiungendo fornitore ID:", fornitore_id)  # Debug: stampa il fornitore_id corrente
                LavoroFornitore.objects.create(lavoro=work, fornitore_id=fornitore_id)

            return JsonResponse({'status': 'success', 'message': 'Fornitori aggiunti con successo'})
        except Exception as e:
            print("Errore:", e)  # Debug: stampa l'errore
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        print("Metodo non consentito")  # Debug: stampa il metodo non consentito
        return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)

@xframe_options_exempt
def aggiungi_fornitori_iframe(request):
    work_id = request.GET.get('work_id')
    fornitori_ids = request.GET.get('fornitori_id', '').split(',')

    if work_id and fornitori_ids:
        try:
            work = get_object_or_404(Lavoro, id=work_id)
            for fornitore_id in fornitori_ids:
                LavoroFornitore.objects.create(lavoro=work, fornitore_id=fornitore_id)
            return redirect(f'/update_work_iframe/{work_id}/')
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Work ID e fornitori IDs sono richiesti'}, status=400)

try:
    # Inizializza il client OpenAI
    with open('C:/Users/rscan/Desktop/script/py/lavoro/MEGestionale/V0.4/AITicket/chiave_api.txt', 'r') as f:
        api_key = f.read().strip()
except FileNotFoundError:
    try:
        # Inizializza il client OpenAI
        with open('C:/Users/yscuo/Desktop/V0.4/AITicket/chiave_api.txt', 'r') as f:
            api_key = f.read().strip()
    except FileNotFoundError:
        try:
            # Inizializza il client OpenAI
            with open('/home/MEgestionaleTest/MEGestionale/AITicket/chiave_api.txt', 'r') as f:
                api_key = f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError("API key file not found in any of the specified paths.")
   

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
    #print("\n\n\nlista",lista)
    out = {}
    #print(fornitoriLong)
    for lavoro in lista:
        out[lavoro] = []
        #print(lavoro)
        for f in lista[lavoro]:
            # Debug: Log the current fornitore ID
            #print(f"Processing fornitore ID: {f}")
            #print("\n\n\nflong",fornitoriLong[f])
            fornitore = fornitoriLong[f].copy()
            fornitore["idR"] = f
            out[lavoro].append(fornitore)
    #print("\n\n\nout",out)    
    return out

def sostituisci_fornitori(dati, fornitori):
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
    #rispostaEstratta = [{'Muratura': [9, 14, 6]}, " Ho scelto {9} perché è specializzato in isolamenti e ha sede a Mestre, vicino al luogo del lavoro, il che garantisce efficienza e rapidità. {14} è stato scelto per la sua competenza generale in muratura e la vicinanza a Mestre Venezia, offrendo un'opzione versatile. {6} è stato incluso per le sue capacità nei rifacimenti del tetto, utile se il tetto è parte del problema, anche se Codevigo Padova è meno vicino. "]
    #rispostaEstratta = [{'Muratore': [11, 24, 26], 'Idraulico': [44, 18, 10], 'Geometra': [52, 63, 70]}, " Ho scelto {11}, {24}, e {26} per i lavori di muratura perchÃ© sono specializzati in restauri e lavori edili, e sono vicino alla zona di lavoro. Per l'idraulico, ho considerato {44}, {18}, e {10} in base alla loro vicinanza e competenze negli impianti idrici. Infine, per il geometra, {52}, {63}, e {70} sono stati scelti per la loro capacitÃ\xa0 di supervisionare e supportare tecnicamente i lavori. "]
    # Debug: Log the extracted response
    #print(f"Extracted Response: {rispostaEstratta}")
    
    #print(rispostaEstratta[1], getFornitori(rispostaEstratta[0]))
    return rispostaEstratta[1], getFornitori(rispostaEstratta[0])

def get_fornitori_from_db():
    fornitori = Fornitore.objects.all()
    fornitori_list = []
    for fornitore in fornitori:
        fornitori_list.append({
            "Categoria": fornitore.categoria.nome if fornitore.categoria else '',
            "Specialità": fornitore.specialita,
            "persone": fornitore.numero_dipendenti,
            "citta": fornitore.luogo
        })
    return fornitori_list
def get_fornitori_long_from_db():
    fornitori = Fornitore.objects.all()
    fornitori_list = []
    for fornitore in fornitori:
        fornitori_list.append({
            "id": fornitore.id,
            "Categoria": fornitore.categoria.nome if fornitore.categoria else '',
            "Specialità": fornitore.specialita,
            "persone": fornitore.numero_dipendenti,
            "citta": fornitore.luogo,
            "Nome": fornitore.descrizione,
            "Telefono": fornitore.cellulari
        })
    return fornitori_list



@csrf_exempt
def update_riferimento(request, id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            riferimento = get_object_or_404(Riferimento, id=id)
            riferimento.nome = data.get('nome', riferimento.nome)
            riferimento.cognome = data.get('cognome', riferimento.cognome)
            riferimento.telefono = data.get('telefono', riferimento.telefono)
            riferimento.email = data.get('email', riferimento.email)
            riferimento.save()
            return JsonResponse({'status': 'success', 'message': 'Riferimento aggiornato con successo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Metodo non consentito'}, status=405)


    

# Fetch suppliers from the database
fornitori = get_fornitori_from_db()
#print(fornitori[:12])
fornitoriLong = get_fornitori_long_from_db()
#print(fornitoriLong[:12])



try:
    # Prepare the prompt with suppliers from the database
    with open('C:/Users/rscan/Desktop/script/py/lavoro/MEGestionale/V0.4/AITicket/promptFornitori.txt', 'r') as f:
        prompt = f.read().strip() + str(fornitori)
except FileNotFoundError:
    try:
        # Prepare the prompt with suppliers from the database
        with open('C:/Users/yscuo/Desktop/V0.4/AITicket/promptFornitori.txt', 'r') as f:
            prompt = f.read().strip() + str(fornitori)
    except FileNotFoundError:
        try:
            # Prepare the prompt with suppliers from the database
            with open('/home/MEgestionaleTest/MEGestionale/AITicket/promptFornitori.txt', 'r') as f:
                prompt = f.read().strip() + str(fornitori)
        except FileNotFoundError:
            raise FileNotFoundError("Prompt file not found in any of the specified paths.")


def store_email_in_sent_folder(email_message, user, password, server="imaps.aruba.it", port=993):
    """
    Salva l'email nella cartella "Sent" del provider Aruba,
    utilizzando IMAP.
    """
    import imaplib
    import email.utils
    import traceback
    
    try:
        print(f"Tentativo di connessione a {server}:{port}...")
        m = imaplib.IMAP4_SSL(server, port)
        print("Connessione stabilita, tentativo di login...")
        m.login(user, password)
        print("Login effettuato con successo, elencando cartelle disponibili...")
        
        # Lista le cartelle disponibili per debug
        status, folders = m.list()
        print(f"Cartelle disponibili: {folders}")
        
        # Dai log, vediamo che la cartella corretta è "INBOX.Sent" con flag \Sent
        try:
            # Usa la cartella Sent corretta da Aruba (dai log precedenti)
            print(f"Tentativo di salvare in INBOX.Sent...")
            # Aggiungi il flag di Seen (letto) all'email
            m.append('INBOX.Sent', '\\Seen', imaplib.Time2Internaldate(time.time()), str(email_message).encode('utf-8'))
            print(f"Email salvata con successo in INBOX.Sent")
        except Exception as folder_error:
            print(f"Errore: {str(folder_error)}")
            
        m.logout()
        print("Logout IMAP completato")
        
        return True
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Errore nel salvataggio email tramite IMAP: {str(e)}")
        print(f"Traceback completo:\n{error_traceback}")
        return False

@csrf_exempt
def send_email(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            to_addresses = data.get('to', [])  # Now expects an array of email addresses
            subject = data.get('subject')
            body = data.get('body')
            attachments = data.get('attachments', [])
            
            if not to_addresses or not subject:
                return JsonResponse({'status': 'error', 'message': 'Recipient and subject are required'}, status=400)
            
            # Save email addresses to the database
            for email in to_addresses:
                EmailAddress.objects.get_or_create(email=email)

            # SMTP Configuration
            SMTP_SERVER = "smtps.aruba.it"
            SMTP_PORT = 465
            USERNAME = "amministrazione@missionedilizia.com"
            PASSWORD = "Ailovolandia4&"
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = USERNAME
            msg['To'] = ', '.join(to_addresses)  # Join multiple recipients with commas
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Process attachments
            for attachment in attachments:
                file_path = None
                
                if '?file=' in attachment:
                    base_path, filename = attachment.split('?file=')
                    filename = unquote(filename)
                    file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', filename)
                else:
                    path_parts = Path(attachment).parts
                    filename = path_parts[-1] if path_parts else 'attachment'
                    file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', filename)
                
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        file_attachment = MIMEApplication(f.read())
                        file_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(file_attachment)
                else:
                    print(f"Warning: Could not find attachment file: {file_path}")
            
            # Send email with SSL
            try:
                with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                    server.login(USERNAME, PASSWORD)
                    server.sendmail(USERNAME, to_addresses, msg.as_string())
                    print("Email inviata con successo con SSL!")
                    
                    # Salvataggio nella cartella Sent
                    saved = store_email_in_sent_folder(
                        msg, 
                        USERNAME, 
                        PASSWORD, 
                        server="imaps.aruba.it"
                    )
                    
                    # Assicuriamoci che la risposta venga restituita
                    message = 'Email inviata con successo.'
                    if saved:
                        message += ' Salvata nella cartella Posta inviata.'
                    
                    return JsonResponse({'status': 'success', 'message': message})
            except Exception as e:
                print(f"Errore nell'invio dell'email: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
        except Exception as e:
            print(f"Email sending error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def get_saved_emails(request):
    emails = EmailAddress.objects.values_list('email', flat=True)
    return JsonResponse(list(emails), safe=False)

# Nuovi endpoint per gestire i nomi personalizzati delle colonne
@csrf_exempt
def get_stage_names(request):
    """Restituisce i nomi personalizzati delle colonne"""
    # Per ora restituiamo i nomi di default, ma in futuro si potrebbe 
    # salvare in un modello o in cache/sessione i nomi personalizzati
    stage_names = {
        "in_sospeso_per_valutazioni": "In sospeso per valutazioni",
        "nuovo_sopralluogo": "Nuovo sopralluogo", 
        "da_preventivare": "Da preventivare",
        "inviato_preventivo": "Inviato preventivo",
        "confermato_da_eseguire": "Confermato da eseguire",
        "con_piattaforma_o_fune": "In corso o In Lavorazione",
        "in_corso": "In corso",
        "da_fatturare": "Da fatturare", 
        "fatturate_da_pagare": "Fatturato da pagare",
        "archiviate": "Archiviate",
        "offerte_perse": "Offerte Perse"
    }
    
    # Recupera i nomi personalizzati dalla sessione se esistono
    custom_names = request.session.get('custom_stage_names', {})
    stage_names.update(custom_names)
    
    return JsonResponse(stage_names)

@csrf_exempt  
def update_stage_name(request):
    """Aggiorna il nome personalizzato di una colonna"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stage_key = data.get('stage_key')
            new_name = data.get('new_name')
            
            if not stage_key or not new_name:
                return JsonResponse({'status': 'error', 'message': 'Parametri mancanti'}, status=400)
            
            # Salva il nome personalizzato nella sessione
            custom_names = request.session.get('custom_stage_names', {})
            custom_names[stage_key] = new_name
            request.session['custom_stage_names'] = custom_names
            request.session.modified = True
            
            return JsonResponse({'status': 'success', 'message': 'Nome colonna aggiornato con successo'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Metodo non supportato'}, status=405)

# Funzione helper per salvare cronologia modifiche
def salva_cronologia(tipo, azione, dettagli, entity_id=None):
    """Salva una modifica nella cronologia"""
    try:
        CronologiaModifiche.objects.create(
            tipo=tipo,
            azione=azione,
            dettagli=dettagli,
            entity_id=entity_id
        )
    except Exception as e:
        print(f"Errore nel salvare cronologia: {e}")

# Endpoint per ottenere la cronologia
def get_cronologia(request):
    """Restituisce la cronologia delle modifiche"""
    try:
        cronologia = CronologiaModifiche.objects.all()[:50]  # Ultimi 50 record
        data = []
        for record in cronologia:
            data.append({
                'id': record.id,
                'tipo': record.get_tipo_display(),
                'azione': record.get_azione_display(),
                'dettagli': record.dettagli,
                'entity_id': record.entity_id,
                'timestamp': record.timestamp.strftime('%d/%m/%Y %H:%M:%S')
            })
        return JsonResponse({'cronologia': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Endpoint per contatti WhatsApp migliorato
def get_whatsapp_contacts_advanced(request, work_id):
    """Restituisce tutti i contatti WhatsApp disponibili per un lavoro con selezione multipla"""
    try:
        lavoro = get_object_or_404(Lavoro, id=work_id)
        contacts = []
        
        # Cliente associato al lavoro
        if lavoro.cliente and lavoro.cliente.cellulare:
            contacts.append({
                'id': f'cliente_{lavoro.cliente.id}',
                'name': lavoro.cliente.descrizione,
                'phone': lavoro.cliente.cellulare,
                'source': 'cliente_associato',
                'type': 'Cliente del ticket'
            })
        
        # Tutti i clienti con cellulare
        for cliente in Cliente.objects.filter(cellulare__isnull=False).exclude(cellulare=''):
            if cliente.id != (lavoro.cliente.id if lavoro.cliente else None):
                contacts.append({
                    'id': f'cliente_{cliente.id}',
                    'name': cliente.descrizione,
                    'phone': cliente.cellulare,
                    'source': 'cliente',
                    'type': 'Cliente'
                })
        
        # Fornitori associati al lavoro
        for lf in lavoro.lavoro_fornitori.all():
            if lf.fornitore.cellulari:
                contacts.append({
                    'id': f'fornitore_{lf.fornitore.id}',
                    'name': lf.fornitore.descrizione,
                    'phone': lf.fornitore.cellulari,
                    'source': 'fornitore_associato',
                    'type': 'Fornitore del ticket'
                })
        
        # Tutti i fornitori con cellulari
        for fornitore in Fornitore.objects.filter(cellulari__isnull=False).exclude(cellulari=''):
            if not lavoro.lavoro_fornitori.filter(fornitore=fornitore).exists():
                contacts.append({
                    'id': f'fornitore_{fornitore.id}',
                    'name': fornitore.descrizione,
                    'phone': fornitore.cellulari,
                    'source': 'fornitore',
                    'type': 'Fornitore'
                })
        
        # Tutti i contatti dalla rubrica
        for contatto in Contatti.objects.filter(telefono__isnull=False).exclude(telefono=''):
            contacts.append({
                'id': f'contatto_{contatto.id}',
                'name': contatto.nome,
                'phone': contatto.telefono,
                'source': 'contatti',
                'type': 'Contatto'
            })
        
        # Riferimento del lavoro
        if lavoro.riferimento and lavoro.riferimento.telefono:
            contacts.append({
                'id': f'riferimento_{lavoro.riferimento.id}',
                'name': f"{lavoro.riferimento.nome} {lavoro.riferimento.cognome}",
                'phone': lavoro.riferimento.telefono,
                'source': 'riferimento',
                'type': 'Riferimento'
            })
        
        return JsonResponse({
            'contacts': contacts,
            'work_info': {
                'id': lavoro.id,
                'numero_ticket': lavoro.id,
                'descrizione': lavoro.descrizione,
                'cliente': lavoro.cliente.descrizione if lavoro.cliente else 'Nessun cliente'
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Endpoint per contatti email migliorato
def get_email_contacts_advanced(request, work_id):
    """Restituisce tutti i contatti email disponibili per un lavoro con selezione multipla"""
    try:
        lavoro = get_object_or_404(Lavoro, id=work_id)
        contacts = []
        
        # Cliente associato al lavoro
        if lavoro.cliente and lavoro.cliente.email:
            contacts.append({
                'id': f'cliente_{lavoro.cliente.id}',
                'name': lavoro.cliente.descrizione,
                'email': lavoro.cliente.email,
                'source': 'cliente_associato',
                'type': 'Cliente del ticket'
            })
        
        # Tutti i clienti con email
        for cliente in Cliente.objects.filter(email__isnull=False).exclude(email=''):
            if cliente.id != (lavoro.cliente.id if lavoro.cliente else None):
                contacts.append({
                    'id': f'cliente_{cliente.id}',
                    'name': cliente.descrizione,
                    'email': cliente.email,
                    'source': 'cliente',
                    'type': 'Cliente'
                })
        
        # Fornitori associati al lavoro
        for lf in lavoro.lavoro_fornitori.all():
            if lf.fornitore.email:
                contacts.append({
                    'id': f'fornitore_{lf.fornitore.id}',
                    'name': lf.fornitore.descrizione,
                    'email': lf.fornitore.email,
                    'source': 'fornitore_associato',
                    'type': 'Fornitore del ticket'
                })
        
        # Tutti i contatti dalla rubrica
        for contatto in Contatti.objects.filter(email__isnull=False).exclude(email=''):
            contacts.append({
                'id': f'contatto_{contatto.id}',
                'name': contatto.nome,
                'email': contatto.email,
                'source': 'contatti',
                'type': 'Contatto'
            })
        
        # Riferimento del lavoro
        if lavoro.riferimento and lavoro.riferimento.email:
            contacts.append({
                'id': f'riferimento_{lavoro.riferimento.id}',
                'name': f"{lavoro.riferimento.nome} {lavoro.riferimento.cognome}",
                'email': lavoro.riferimento.email,
                'source': 'riferimento',
                'type': 'Riferimento'
            })
        
        # Email salvate in precedenza
        for email_obj in EmailAddress.objects.all():
            contacts.append({
                'id': f'saved_{email_obj.id}',
                'name': email_obj.email,
                'email': email_obj.email,
                'source': 'saved',
                'type': 'Email salvata'
            })
        
        return JsonResponse({
            'contacts': contacts,
            'work_info': {
                'id': lavoro.id,
                'numero_ticket': lavoro.id,
                'descrizione': lavoro.descrizione,
                'cliente': lavoro.cliente.descrizione if lavoro.cliente else 'Nessun cliente'
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Funzioni di compatibilità per i vecchi endpoint
def get_whatsapp_contacts(request, work_id):
    """Wrapper per compatibilità con il vecchio endpoint WhatsApp"""
    try:
        # Chiama la versione avanzata e adatta il formato
        response = get_whatsapp_contacts_advanced(request, work_id)
        data = json.loads(response.content)
        
        # Adatta il formato per compatibilità
        if 'contacts' in data:
            return JsonResponse({
                'status': 'success',
                'contacts': data['contacts'],
                'work_info': data.get('work_info', {})
            })
        else:
            return response
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_email_contacts(request, work_id):
    """Wrapper per compatibilità con il vecchio endpoint Email"""
    try:
        # Chiama la versione avanzata e adatta il formato
        response = get_email_contacts_advanced(request, work_id)
        data = json.loads(response.content)
        
        # Adatta il formato per compatibilità
        if 'contacts' in data:
            return JsonResponse({
                'status': 'success',
                'contacts': data['contacts'],
                'work_info': data.get('work_info', {})
            })
        else:
            return response
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Nuovi endpoint per contatti solo del ticket specifico
def get_whatsapp_contacts_ticket_only(request, work_id):
    """Restituisce solo i contatti WhatsApp del ticket specifico (cliente, fornitori associati, riferimento)"""
    try:
        lavoro = get_object_or_404(Lavoro, id=work_id)
        contacts = []
        
        # Cliente associato al lavoro
        if lavoro.cliente and lavoro.cliente.cellulare:
            contacts.append({
                'id': f'cliente_{lavoro.cliente.id}',
                'name': lavoro.cliente.descrizione,
                'phone': lavoro.cliente.cellulare,
                'source': 'cliente_associato',
                'type': 'Cliente del ticket'
            })
        
        # Fornitori associati al lavoro
        for lf in lavoro.lavoro_fornitori.all():
            if lf.fornitore.cellulari:
                contacts.append({
                    'id': f'fornitore_{lf.fornitore.id}',
                    'name': lf.fornitore.descrizione,
                    'phone': lf.fornitore.cellulari,
                    'source': 'fornitore_associato',
                    'type': 'Fornitore del ticket'
                })
        
        # Riferimento del lavoro
        if lavoro.riferimento and lavoro.riferimento.telefono:
            contacts.append({
                'id': f'riferimento_{lavoro.riferimento.id}',
                'name': f"{lavoro.riferimento.nome} {lavoro.riferimento.cognome}",
                'phone': lavoro.riferimento.telefono,
                'source': 'riferimento',
                'type': 'Riferimento'
            })
        
        # Processa i contatti per validare i numeri
        processed_contacts = []
        for contact in contacts:
            phone = contact['phone']
            valid_numbers = []
            
            # Se il numero contiene virgole, dividi
            if ',' in phone:
                numbers = [num.strip() for num in phone.split(',')]
            else:
                numbers = [phone.strip()]
            
            # Valida ogni numero
            for num in numbers:
                if num and len(num) >= 8:  # Numero minimo valido
                    valid_numbers.append(num)
            
            if valid_numbers:
                processed_contacts.append({
                    **contact,
                    'validNumbers': valid_numbers
                })
        
        return JsonResponse({
            'contacts': processed_contacts,
            'work_info': {
                'id': lavoro.id,
                'numero_ticket': lavoro.id,
                'descrizione': lavoro.descrizione,
                'cliente': lavoro.cliente.descrizione if lavoro.cliente else 'Nessun cliente'
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_email_contacts_ticket_only(request, work_id):
    """Restituisce solo i contatti email del ticket specifico (cliente, fornitori associati, riferimento)"""
    try:
        lavoro = get_object_or_404(Lavoro, id=work_id)
        contacts = []
        
        # Cliente associato al lavoro
        if lavoro.cliente and lavoro.cliente.email:
            contacts.append({
                'id': f'cliente_{lavoro.cliente.id}',
                'name': lavoro.cliente.descrizione,
                'email': lavoro.cliente.email,
                'source': 'cliente_associato',
                'type': 'Cliente del ticket'
            })
        
        # Fornitori associati al lavoro
        for lf in lavoro.lavoro_fornitori.all():
            if lf.fornitore.email:
                contacts.append({
                    'id': f'fornitore_{lf.fornitore.id}',
                    'name': lf.fornitore.descrizione,
                    'email': lf.fornitore.email,
                    'source': 'fornitore_associato',
                    'type': 'Fornitore del ticket'
                })
        
        # Riferimento del lavoro
        if lavoro.riferimento and lavoro.riferimento.email:
            contacts.append({
                'id': f'riferimento_{lavoro.riferimento.id}',
                'name': f"{lavoro.riferimento.nome} {lavoro.riferimento.cognome}",
                'email': lavoro.riferimento.email,
                'source': 'riferimento',
                'type': 'Riferimento'
            })
        
        return JsonResponse({
            'contacts': contacts,
            'work_info': {
                'id': lavoro.id,
                'numero_ticket': lavoro.id,
                'descrizione': lavoro.descrizione,
                'cliente': lavoro.cliente.descrizione if lavoro.cliente else 'Nessun cliente'
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

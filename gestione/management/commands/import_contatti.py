import json
from django.core.management.base import BaseCommand
from gestione.models import Contatti
from django.utils.dateparse import parse_date
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa i contatti da un file JSON'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Il percorso al file di contatti')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        # Legge il file JSON
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        for item in data:
            # Rimuove gli spazi dai numeri di telefono
            telefono = item.get('Telefono', '').replace(" ", "")

            # Converte la data al formato YYYY-MM-DD
            data_creazione_str = item.get('Creato', '')
            data_creazione = None
            if data_creazione_str:
                try:
                    data_creazione = datetime.strptime(data_creazione_str, '%d/%m/%Y').date()
                except ValueError:
                    self.stdout.write(self.style.WARNING(f"Formato data non valido per {data_creazione_str}. Sarà impostata a None."))

            # Crea un'istanza di Contatti per ciascun elemento
            contatto = Contatti(
                nome=item.get('Nome', ''),
                n_dipendenti=item.get('NDipendenti', ''),
                telefono=telefono,
                sito=item.get('Sito', ''),
                creato=data_creazione,
                email=item.get('email', ''),
                categoria=item.get('Categoria', ''),
                partita_iva=item.get('PIVA', ''),
                specialita=item.get('Specialità', ''),
                citta=item.get('citta', ''),
            )
            contatto.save()  # Salva l'istanza nel database

        self.stdout.write(self.style.SUCCESS('Importazione completata con successo'))

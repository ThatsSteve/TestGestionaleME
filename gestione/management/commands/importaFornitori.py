import csv
from difflib import get_close_matches
from django.core.management.base import BaseCommand
from gestione.models import Fornitore, Categoria

class Command(BaseCommand):
    help = 'Importa fornitori da fornitori.csv'

    def handle(self, *args, **kwargs):
        with open('fornitori.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                azienda = row['Azienda']
                dipendenti = row['Dipendenti']
                telefono = row['Telefono']
                sito_web = row['Sito Web']
                categoria_nome = row['Categoria'] or "categoria non specificata"
                partita_iva = row['Partita IVA']
                specialita = row['Specialità']
                citta = row['Città']

                # Check for similar names
                existing_fornitori = Fornitore.objects.values_list('descrizione', flat=True)
                if azienda in existing_fornitori:
                    print(f"Fornitore {azienda} già esistente. Saltato.")
                    continue

                similar_names = get_close_matches(azienda, existing_fornitori, n=1, cutoff=0.8)
                
                if similar_names:
                    print(f"Trovato nome simile: {similar_names[0]} per {azienda}. Aggiungere comunque? (s/n)")
                    response = input().strip().lower()
                    if response != 's':
                        continue

                # Get or create category
                categoria, created = Categoria.objects.get_or_create(nome=categoria_nome)

                # Create new supplier
                Fornitore.objects.create(
                    descrizione=azienda,
                    numero_dipendenti=dipendenti,
                    cellulari=telefono,
                    sito_web=sito_web,
                    categoria=categoria,
                    partita_iva=partita_iva,
                    specialita=specialita,
                    luogo=citta
                )
                print(f"Fornitore {azienda} aggiunto con successo.")

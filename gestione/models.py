from django.db import models
from django.utils import timezone





class Categoria(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome



class Cliente(models.Model):
    descrizione = models.CharField(max_length=255)
    nome = models.CharField(max_length=255, null=True, blank=True)
    cognome = models.CharField(max_length=255, null=True, blank=True)
    cellulare = models.CharField(max_length=50,  null=True, blank=True)
    indirizzo = models.CharField(max_length=255, null=True, blank=True)  # Nuovo campo
    email = models.EmailField(null=True, blank=True)  # Nuovo campo
    societa = models.BooleanField(default=False)  # Nuovo campo
    piva = models.CharField(max_length=50, null=True, blank=True)  # Nuovo campo
    codice_fiscale = models.CharField(max_length=16, null=True, blank=True)  # Nuevo campo

    def __str__(self):
        return self.descrizione


class Riferimento(models.Model):
    nome = models.CharField(max_length=255)
    cognome = models.CharField(max_length=255)
    telefono = models.CharField(max_length=50)
    email = models.EmailField()

    def __str__(self):
        return f"{self.nome} {self.cognome}"



class Contatti(models.Model):
    nome = models.CharField(max_length=255)
    n_dipendenti = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    sito = models.URLField(blank=True, null=True)
    creato = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    partita_iva = models.CharField(max_length=20, blank=True, null=True)
    specialita = models.TextField(blank=True, null=True)
    citta = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    cronologia = models.TextField(blank=True, null=True)
    recensioni = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

class Fornitore(models.Model):
    descrizione = models.CharField(max_length=255)
    nome = models.CharField(max_length=100, null=True)
    cognome = models.CharField(max_length=100, null=True)
    attivita = models.CharField(max_length=255, null=True)
    cellulari = models.CharField(max_length=255, null=True)
    numero_dipendenti = models.CharField(max_length=50, null=True)
    sito_web = models.CharField(max_length=255, null=True)
    email = models.CharField(max_length=255, null=True)
    partita_iva = models.CharField(max_length=50, null=True)
    specialita = models.TextField(null=True)
    luogo = models.CharField(max_length=255, null=True)
    note = models.TextField(null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='fornitori', null=True)
    codice_fiscale = models.CharField(max_length=16, null=True, blank=True)  # Nuevo campo
    affidabilita = models.FloatField(null=True, blank=True)  # Campo per valutare l'affidabilità

    def __str__(self):
        return self.descrizione


class Lavoro(models.Model):
    descrizione = models.TextField()
    fase = models.CharField(max_length=100)
    importo = models.FloatField(default=0.0)
    data_creazione = models.DateTimeField(default=timezone.now)
    note = models.TextField()
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='lavori', null=True)
    position = models.IntegerField(default=0)
    riferimento = models.ForeignKey('Riferimento', on_delete=models.SET_NULL, null=True, blank=True)
    selezionato = models.BooleanField(default=False)

    def __str__(self):
        return f"Lavoro: {self.descrizione}, Cliente: {self.cliente}"


class LavoroFornitore(models.Model):
    lavoro = models.ForeignKey(Lavoro, on_delete=models.CASCADE, related_name='lavoro_fornitori')
    fornitore = models.ForeignKey(Fornitore, on_delete=models.CASCADE)
    confermato = models.BooleanField(default=False)  # New field

    def __str__(self):
        return f"Lavoro: {self.lavoro.descrizione}, Fornitore: {self.fornitore.descrizione}"


class Comment(models.Model):
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    work = models.ForeignKey(Lavoro, on_delete=models.CASCADE, related_name='comments')
    attachment = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Commento su {self.work}: {self.content[:30]}"


class EmailAddress(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class CronologiaModifiche(models.Model):
    TIPO_CHOICES = [
        ('ticket', 'Ticket'),
        ('column', 'Colonna'),
        ('client', 'Cliente'),
        ('supplier', 'Fornitore'),
        ('reference', 'Riferimento'),
        ('work', 'Lavoro'),
    ]
    
    AZIONE_CHOICES = [
        ('create', 'Creazione'),
        ('update', 'Modifica'),
        ('delete', 'Eliminazione'),
        ('move', 'Spostamento'),
        ('rename', 'Rinomina'),
        ('add', 'Aggiunta'),
        ('remove', 'Rimozione'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    azione = models.CharField(max_length=20, choices=AZIONE_CHOICES)
    dettagli = models.TextField()
    entity_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Cronologia Modifica'
        verbose_name_plural = 'Cronologia Modifiche'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.get_azione_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

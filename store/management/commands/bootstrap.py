from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Prepare the database and load Powerloom presentation data."

    def handle(self, *args, **options):
        self.stdout.write("Preparing database schema...")
        call_command("makemigrations", "store", interactive=False, verbosity=0)
        call_command("migrate", interactive=False, verbosity=1)
        call_command("seed_demo")
        self.stdout.write(self.style.SUCCESS("Powerloom is ready at http://127.0.0.1:8000/"))

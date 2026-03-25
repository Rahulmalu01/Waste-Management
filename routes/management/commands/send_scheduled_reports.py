from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from alerts.telegram_service import send_telegram_message
from routes.services_reporting import get_report_summary, build_summary_text


class Command(BaseCommand):
    help = 'Send scheduled daily or weekly management reports via email and Telegram.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='daily',
            choices=['daily', 'weekly'],
            help='Type of report: daily or weekly'
        )
        parser.add_argument(
            '--email-only',
            action='store_true',
            help='Send report only by email'
        )
        parser.add_argument(
            '--telegram-only',
            action='store_true',
            help='Send report only by Telegram'
        )

    def handle(self, *args, **options):
        report_type = options['type']
        email_only = options['email_only']
        telegram_only = options['telegram_only']

        report_data = get_report_summary(report_type=report_type)
        summary_text = build_summary_text(report_data)

        subject = f"{report_type.title()} Waste Management Report"

        email_sent = False
        telegram_sent = False

        if not telegram_only:
            recipient_list = getattr(settings, 'MANAGER_REPORT_EMAILS', [])
            if recipient_list:
                send_mail(
                    subject=subject,
                    message=summary_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
                email_sent = True

        if not email_only:
            telegram_result = send_telegram_message(f"<pre>{summary_text}</pre>")
            telegram_sent = telegram_result.get('success', False)

        self.stdout.write(self.style.SUCCESS(
            f"{report_type.title()} report processed. Email sent: {email_sent}, Telegram sent: {telegram_sent}"
        ))
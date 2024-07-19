# from django.core.mail import EmailMessage
# import random
# from django.conf import settings
# from django.contrib.sites.shortcuts import get_current_site





# def send_normal_email(data):
#     email=EmailMessage(
#         subject=data['email_subject'],
#         body=data['email_body'],
#         from_email=settings.EMAIL_HOST_USER,
#         to=[data['to_email']]
#     )
#     email.send()


# my_app/email_util.py

# jennie/base/utils.py




# jennie/base/utils.py

# jennie/base/utils.py

# jennie/base/utils.py



# jennie/base/utils.py

from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.utils.html import strip_tags
from django.conf import settings

def send_normal_email(data):
    # Load and render the template with context
    template = Template(data['email_body'])
    context = Context(data.get('context', {}))
    html_content = template.render(context)
    text_content = strip_tags(html_content)  # Fallback text content

    # Create email message
    email = EmailMultiAlternatives(
        subject=data['email_subject'],
        body=html_content,  # Plain text content for email clients that don't support HTML
        from_email=settings.EMAIL_HOST_USER,
        to=[data['to_email']],
    )
    email.attach_alternative(html_content, "text/html")  # Attach the HTML version

    # Send email
    email.send()

from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save, pre_save
from .models import ChatSession,ChatMessage,Profile
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

@receiver(pre_save,sender=ChatSession)
def sender_receiver_no_same(sender,instance,**kwargs):
    if instance.user1 == instance.user2:
        raise ValidationError("Sender and Receiver are not same!!",code='Invalid')

@receiver(post_save,sender=User)
def at_ending_save(sender,instance,created,**kwargs):
    if created:
        Profile.objects.create(user = instance)

@receiver(pre_save,sender=ChatMessage)
def user_must_sender_or_receiver(sender,instance,**kwargs):
    if instance.user != instance.chat_session.user1 and instance.user != instance.chat_session.user2:
        instance.delete()
        raise ValidationError("Invalid sender!!",code='Invalid')
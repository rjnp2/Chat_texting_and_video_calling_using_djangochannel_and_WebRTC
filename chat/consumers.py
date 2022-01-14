from channels.generic.websocket import AsyncWebsocketConsumer
import json
from datetime import datetime
from .models import ChatSession, ChatMessage
from channels.db import database_sync_to_async
import uuid
from .models import Profile
from django.db.models import Q

MESSAGE_MAX_LENGTH = 50

MESSAGE_ERROR_TYPE = {
    "MESSAGE_OUT_OF_LENGTH": 'MESSAGE_OUT_OF_LENGTH',
    "UN_AUTHENTICATED": 'UN_AUTHENTICATED',
    "INVALID_MESSAGE": 'INVALID_MESSAGE',
}

MESSAGE_TYPE = {
    "WENT_ONLINE": 'WENT_ONLINE',
    "WENT_OFFLINE": 'WENT_OFFLINE',
    "IS_TYPING": 'IS_TYPING',
    "NOT_TYPING": 'NOT_TYPING',
    "MESSAGE_COUNTER": 'MESSAGE_COUNTER',
    "OVERALL_MESSAGE_COUNTER": 'OVERALL_MESSAGE_COUNTER',
    "TEXT_MESSAGE": 'TEXT_MESSAGE',
    "MESSAGE_READ": 'MESSAGE_READ',
    "ALL_MESSAGE_READ": 'ALL_MESSAGE_READ',
    "ERROR_OCCURED": 'ERROR_OCCURED',
    "offer":"offer",
    "answer":"answer",
    "stop":"stop",
    "candidate":"candidate",
}

class PersonalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'personal__{self.room_name}'
        self.user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        if self.scope["user"].is_authenticated:
            await self.accept()
        else:
            await self.close(code=4001)
            
    async def disconnect(self, code):
        self.set_offline()
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('msg_type')
        user_id = data.get('user_id')
        
        if msg_type == MESSAGE_TYPE['WENT_ONLINE']:
            users_room_id = await self.set_online(user_id)
            for room_id in users_room_id:
                await self.channel_layer.group_send(
                    f'personal__{room_id}',
                    {
                    'type': 'user_online',
                    'user_name' : self.user.username
                    }
                )
        elif msg_type == MESSAGE_TYPE['WENT_OFFLINE']:
            users_room_id = await self.set_offline(user_id)
            for room_id in users_room_id:
                await self.channel_layer.group_send(
                    f'personal__{room_id}',
                    {
                    'type': 'user_offline',
                    'user_name' : self.user.username
                    }
                )
            
    async def user_online(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['WENT_ONLINE'],
            'user_name' : event['user_name']
        }))
        
    async def message_counter(self, event):
        overall_unread_msg = await self.count_unread_overall_msg(event['current_user_id'])
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['MESSAGE_COUNTER'],
            'user_id': event['user_id'],
            'overall_unread_msg' : overall_unread_msg
        }))

    async def user_offline(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['WENT_OFFLINE'],
            'user_name' : event['user_name']
        }))
    
    @database_sync_to_async
    def set_online(self,user_id):
        Profile.objects.filter(user__id = user_id).update(is_online = True)
        user_all_friends = ChatSession.objects.filter(Q(user1 = self.user) | Q(user2 = self.user))
        user_id = []
        for ch_session in user_all_friends:
            user_id.append(ch_session.user2.id) if self.user.username == ch_session.user1.username else user_id.append(ch_session.user1.id)
        return user_id

    @database_sync_to_async
    def set_offline(self,user_id):
        Profile.objects.filter(user__id = user_id).update(is_online = False)
        user_all_friends = ChatSession.objects.filter(Q(user1 = self.user) | Q(user2 = self.user))
        user_id = []
        for ch_session in user_all_friends:
            user_id.append(ch_session.user2.id) if self.user.username == ch_session.user1.username else user_id.append(ch_session.user1.id)
        return user_id

    @database_sync_to_async
    def count_unread_overall_msg(self,user_id):
        return ChatMessage.count_overall_unread_msg(user_id)
    

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = self.room_name
        self.user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        if self.scope["user"].is_authenticated:
            await self.accept()
        else:
            await self.accept()
            await self.send(text_data=json.dumps({
                "msg_type": MESSAGE_TYPE['ERROR_OCCURED'],
                "error_message": MESSAGE_ERROR_TYPE["UN_AUTHENTICATED"],
                "user": self.user.username,
            }))
            await self.close(code=4001)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('msg_type')
        fromUser= data.get('fromUser')
        toUser= data.get('toUser')
        is_video = data.get('is_video')
        print(msg_type)

        if msg_type == MESSAGE_TYPE['TEXT_MESSAGE']:
            message = data.get('message')

            if len(message) <= MESSAGE_MAX_LENGTH:
                msg_id = uuid.uuid4()

                current_user_id = await self.save_text_message(msg_id,message)

                if current_user_id != 'error':
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'msg_id' : str(msg_id),
                            'fromUser': fromUser,
                            'toUser':toUser
                        }
                    )
                    await self.channel_layer.group_send(
                        f'personal__{current_user_id}',
                        {
                            'type': 'message_counter',
                            'user_id' : self.user.id,
                            'current_user_id' : current_user_id
                        }
                    )
                else:
                    await self.send(text_data=json.dumps({
                        'msg_type': MESSAGE_TYPE['ERROR_OCCURED'],
                        'error_message': "user or chat session id doesn't match",
                        'message': message,
                        'timestampe': str(datetime.now()),
                        'fromUser': fromUser,
                        'toUser':toUser
                    }))
            else:
                await self.send(text_data=json.dumps({
                    'msg_type': MESSAGE_TYPE['ERROR_OCCURED'],
                    'error_message': MESSAGE_ERROR_TYPE["MESSAGE_OUT_OF_LENGTH"],
                    'message': message,
                    'timestampe': str(datetime.now()),
                    'fromUser': fromUser,
                    'toUser':toUser
                }))

        elif msg_type == MESSAGE_TYPE['MESSAGE_READ']:
            msg_id = data['msg_id']
            await self.msg_read(msg_id)
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'msg_as_read',
                    'msg_id': msg_id,
                    'fromUser': data.get('fromUser'),
                    'toUser':data.get('toUser')
                    }
                )  

        elif msg_type == MESSAGE_TYPE['ALL_MESSAGE_READ']:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'all_msg_read',
                    'fromUser': data.get('fromUser'),
                    'toUser':data.get('toUser')
                    }
                )
            await self.read_all_msg(self.room_name[5:],fromUser)

        elif msg_type == MESSAGE_TYPE['IS_TYPING']:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'user_is_typing',
                    'fromUser': data.get('fromUser'),
                    'toUser':data.get('toUser')
                    }
                )

        elif msg_type == MESSAGE_TYPE["NOT_TYPING"]:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'user_not_typing',
                   'fromUser': data.get('fromUser'),
                    'toUser':data.get('toUser')
                    }
                )

        elif msg_type == MESSAGE_TYPE["offer"]:
            offer = data.get('offer')

            # to notify the callee we sent an event to the group name
            # and their's groun name is the name
            msg_id = uuid.uuid4()
            await self.channel_layer.group_send(
                     self.room_group_name,
                    {
                    'type': 'user_calling',
                    'fromUser': fromUser,
                    'toUser':toUser,
                    'offer': offer,
                    'msg_id' : str(msg_id),
                    'is_video': is_video
                    }
                )
            
            mess = f'Calling by {fromUser}'
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': mess,
                        'msg_id' : str(msg_id),
                        'fromUser': fromUser,
                        'toUser':toUser
                    }
                )            
            current_user_id = await self.save_text_message(msg_id,mess)
            await self.channel_layer.group_send(
                f'personal__{current_user_id}',
                {
                    'type': 'message_counter',
                    'user_id' : self.user.id,
                    'current_user_id' : current_user_id
                }
            )

        elif msg_type == MESSAGE_TYPE["answer"]:
            answer = data.get('answer')
            # has received call from someone now notify the calling user
            # we can notify to the group with the caller name
            
            await self.channel_layer.group_send(
                     self.room_group_name,
                    {
                    'type': 'user_answer_call',
                    'answer': answer,
                    'fromUser': fromUser,
                    'toUser':toUser
                    }
                )

        elif msg_type == MESSAGE_TYPE["candidate"]:
            candidate = data.get('candidate')
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'ICEcandidate',
                    'candidate': candidate,
                    'fromUser': fromUser,
                    'toUser':toUser
                    }
                )

        elif msg_type == MESSAGE_TYPE["stop"]:
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                    'type': 'stop_message',
                    'fromUser': fromUser,
                    'toUser':toUser
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['TEXT_MESSAGE'],
            'message': event['message'],
            'timestampe': str(datetime.now()),
            'msg_id' : event["msg_id"],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def msg_as_read(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['MESSAGE_READ'],
            'msg_id': event['msg_id'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def all_msg_read(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['ALL_MESSAGE_READ'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def user_is_typing(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['IS_TYPING'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def user_not_typing(self,event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['NOT_TYPING'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))
    
    async def user_calling(self, event):

        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['offer'],
            'offer': event['offer'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def user_answer_call(self, event):

        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['answer'],
            'answer': event['answer'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    async def ICEcandidate(self, event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['candidate'],
            'candidate': event['candidate'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))
    
    async def stop_message(self, event):
        await self.send(text_data=json.dumps({
            'msg_type': MESSAGE_TYPE['stop'],
            'fromUser':  event["fromUser"],
            'toUser': event["toUser"]
        }))

    @database_sync_to_async
    def save_text_message(self,msg_id,message):
        session_id = self.room_name[5:]

        session_inst = ChatSession.objects.select_related('user1', 'user2').filter( Q(id = session_id))

        if session_inst.exists():
            session_inst = session_inst.first()
            message_json = {
                "msg": message,
                "read": False,
                "timestamp": str(datetime.now()),
                session_inst.user1.username: False,
                session_inst.user2.username: False
            }
            ChatMessage.objects.create(id = msg_id,chat_session=session_inst, user=self.user, message_detail=message_json)
            return session_inst.user2.id if self.user == session_inst.user1 else session_inst.user1.id
        
        else:
            return 'error'
    
    @database_sync_to_async
    def msg_read(self,msg_id):
        return ChatMessage.meassage_read_true(msg_id)

    @database_sync_to_async
    def read_all_msg(self,room_id,user):
        return ChatMessage.all_msg_read(room_id,user)
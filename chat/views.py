from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import *
from django.http.response import HttpResponse, HttpResponseRedirect
from django.contrib import messages

@login_required
def home(request, room_name=None):
    # count all unread message
    unread_msg = ChatMessage.count_overall_unread_msg(request.user.id)

    #find all chatting friend list
    user_inst = request.user
    user_all_friends = ChatSession.objects.filter(Q(user1 = user_inst) | Q(user2 = user_inst)).select_related('user1','user2').order_by('-updated_on')
    all_friends = []

    for ch_session in user_all_friends:
        user,user_inst = [ch_session.user2,ch_session.user1] if request.user.username == ch_session.user1.username else [ch_session.user1,ch_session.user2]
        un_read_msg_count = ChatMessage.objects.filter(chat_session = ch_session.id,message_detail__read = False).exclude(user = user_inst).count()        
        data = {
            "user_name" : user.username,
            "room_name" : ch_session.room_group_name,
            "un_read_msg_count" : un_read_msg_count,
            "status" : user.profile_detail.is_online,
            "user_id" : user.id
        }
        all_friends.append(data)
    
    #find all suggested friend list
    user_1 = request.user
    user_all_friends = ChatSession.objects.filter(Q(user1 = user_1) | Q(user2 = user_1))
    user_list = []
    for ch_session in user_all_friends:
        user_list.append(ch_session.user1.id)
        user_list.append(ch_session.user2.id)
    all_user = User.objects.exclude(Q(username=user_1.username)|Q(id__in = list(set(user_list))))

    # extracting all message of given room name
    opposite_user = None
    fetch_all_message= None

    if room_name:
        current_user = request.user
        try:
            check_user = ChatSession.objects.filter(Q(id = room_name[5:])&(Q(user1 = current_user)|Q(user2 = current_user)))
        except Exception:
            return HttpResponse("Something went wrong!!!")
        if check_user.exists():
            chat_user_pair = check_user.first()
            opposite_user = chat_user_pair.user2 if chat_user_pair.user1.username == current_user.username else chat_user_pair.user1
            fetch_all_message = ChatMessage.objects.filter(chat_session__id = room_name[5:]).order_by('message_detail__timestamp')
        else:
            return HttpResponse("You have't permission to chatting with this user!!!")
    
    context = {'unread_msg':unread_msg,
               'user_list': all_friends,
               'all_user' : all_user,
               'room_name' : room_name,
                'opposite_user' : opposite_user,
                'fetch_all_message' : fetch_all_message}

    return render(request, 'chat/home.html', context)

@login_required
def create_friend(request,id):
    user_1 = request.user
    user_2 = get_object_or_404(User,id = id)
    get_create = ChatSession.create_if_not_exists(user_1,user_2)
    if get_create:
        room_name = get_create.room_group_name
        print(room_name)
        messages.add_message(request,messages.SUCCESS,f'{user_2.username} successfully added in your chat list!!')
        return redirect(f'/{room_name}')
    else:
        messages.add_message(request,messages.SUCCESS,f'{user_2.username} already added in your chat list!!')
    return redirect('/')
    
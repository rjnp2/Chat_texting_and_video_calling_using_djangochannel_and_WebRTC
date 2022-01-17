from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .forms import LoginForm, UserForm

def login_page(request):
    forms = LoginForm()
    if request.method == 'POST':
        forms = LoginForm(request.POST)
        if forms.is_valid():
            username = forms.cleaned_data['username']
            password = forms.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect('/')

    context = {'form': forms}
    return render(request, 'user/login.html', context)

@login_required
def logout_page(request):
    logout(request)
    print('logout')
    return redirect('/user/login')

def register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            print('sucess')
            return redirect('/user/login')
        else:
            print(form.errors)
            form = UserForm()
    else:
        form = UserForm()

    context = {
        'form': form
    }
    return render(request, 'user/register.html',context)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .forms import LoginForm, UserRegisterForm

def login_page(request):
    if request.method == 'POST':
        forms = LoginForm(request.POST)
        if forms.is_valid():
            username = forms.cleaned_data['username']
            password = forms.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect('/')
    else:
        forms = LoginForm()

    context = {'form': forms}
    return render(request, 'user/login.html', context)

@login_required
def logout_page(request):
    print('logout')
    return redirect('/user/login')

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/user/login')

    else:
        form = UserRegisterForm()

    context = {
        'form': form
    }
    return render(request, 'user/register.html',context)
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from django.contrib import messages

def auth_view(request):
    if request.method == 'POST':
        if 'name' in request.POST:
            return handle_register(request)
        else:
            return handle_login(request)
    
    return render(request, 'login.html')

def handle_register(request):
    name = request.POST.get('name')
    email = request.POST.get('email')
    password = request.POST.get('password')

    if User.objects.filter(username=name).exists():
        messages.error(request, 'Este nome de usuário já existe!')
        return redirect('auth')
    
    if User.objects.filter(email=email).exists():
        messages.error(request, 'Este email de usuário já existe!')
        return redirect('auth')

    try:
        user = User.objects.create_user(
            username=name,
            email=email,
            password=password
        )
        
        user = authenticate(request, username=name, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('home')
        else:
            messages.error(request, 'Erro na autenticação do novo usuário!')
    except Exception as e:
        messages.error(request, f'Erro ao criar o Usuário: {e}.')
        return redirect('auth')
    
def handle_login(request):
    email = request.POST.get('email')
    password = request.POST.get('password')

    try:
        user = User.objects.get(email=email)
        username = user.username
    except User.DoesNotExist:
        messages.error(request, 'Email ou senha inválido.')
        return redirect('auth')
    
    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        messages.success(request, 'Login realizado com sucesso.')
        return redirect('home')
    else:
        messages.error(request, 'Email ou senha inválido!')
        return redirect('auth')
    
def logout_view(request):
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('auth')

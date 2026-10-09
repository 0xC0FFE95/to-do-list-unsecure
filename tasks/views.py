import hashlib
import json
import logging
import os
import secrets
import yaml

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import escape
from django.views.decorators.http import require_http_methods

from .forms import TaskForm
from .models import Task

logger = logging.getLogger(__name__)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Sup3rS3cret!123")


def generate_token():
    return secrets.token_hex(16)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256((salt + password).encode()).hexdigest()


def load_config(path="config.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


def notify_new_task(title: str):
    logger.info("Nouvelle tâche créée : %s", title)


@require_http_methods(["GET", "POST"])
def index(request):
    tasks = Task.objects.all()
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            logger.info("Tâche ajoutée : %s", task.title)
            notify_new_task(task.title)
            return redirect("/")

    context = {
        "tasks": tasks,
        "form": form,
        "welcome_message": "Bienvenue sur votre TO DO LIST !",
    }
    return render(request, "tasks/list.html", context)


@require_http_methods(["GET", "POST"])
def update_task(request, pk):
    task = get_object_or_404(Task, id=pk)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            logger.info("Tâche modifiée : %s", task.title)
            return redirect("/")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


@require_http_methods(["GET", "POST"])
def delete_task(request, pk):
    item = get_object_or_404(Task, id=pk)

    if request.method == "POST":
        item.delete()
        logger.info("Tâche supprimée : %s", item.title)
        return redirect("/")

    context = {"item": item}
    return render(request, "tasks/delete.html", context)


@require_http_methods(["GET"])
def search_tasks(request):
    query = request.GET.get("q", "")
    tasks = Task.objects.filter(title__icontains=query) if query else []
    results = "".join(f"<li>{escape(t.title)}</li>" for t in tasks)
    return HttpResponse(f"<ul>{results}</ul>")


@require_http_methods(["GET", "POST"])
def import_tasks(request):
    if request.method == "POST":
        data = request.POST.get("tasks_data", "")
        try:
            tasks = json.loads(data)
            if isinstance(tasks, list):
                for t in tasks:
                    if isinstance(t, str) and t.strip():
                        Task.objects.create(title=t.strip())
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Échec de l'import des tâches : format JSON invalide")

        return redirect("/")

    return HttpResponse(
        "<form method='post'><input name='tasks_data'><input type='submit'></form>"
    )


@require_http_methods(["GET"])
def admin_panel(request):
    password = request.GET.get("pwd", "")
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        return HttpResponse("Bienvenue admin !")
    return HttpResponse("Accès refusé", status=403)

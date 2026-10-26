from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.accounts.models import User

from .models import Attachment, Comment, Ticket, TicketHistory


class TicketQuerysetMixin:
    def get_queryset(self):
        qs = Ticket.objects.select_related(
            "category", "priority", "assigned_to", "customer"
        )
        if self.request.user.role == User.Role.CUSTOMER:
            qs = qs.filter(customer=self.request.user)
        return qs


class TicketListView(LoginRequiredMixin, TicketQuerysetMixin, ListView):
    model = Ticket
    paginate_by = 20
    context_object_name = "ticket_list"


class TicketDetailView(LoginRequiredMixin, TicketQuerysetMixin, DetailView):
    model = Ticket
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comments = self.object.comments.select_related("user").prefetch_related(
            "attachments"
        )
        if self.request.user.role == User.Role.CUSTOMER:
            comments = comments.filter(is_internal=False)
        context["comments"] = comments
        context["attachments"] = self.object.attachments.filter(comment__isnull=True)
        context["histories"] = self.object.histories.select_related("user")[:15]
        return context


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    fields = ("title", "description", "category", "priority", "due_date")
    success_url = reverse_lazy("tickets:list")

    def form_valid(self, form):
        form.instance.customer = self.request.user
        response = super().form_valid(form)
        TicketHistory.objects.create(
            ticket=self.object,
            user=self.request.user,
            action="Tạo ticket mới",
            new_value=f"Tiêu đề: {self.object.title}",
        )
        return response


class TicketUpdateView(LoginRequiredMixin, TicketQuerysetMixin, UpdateView):
    model = Ticket
    success_url = reverse_lazy("tickets:list")

    def get_fields(self):
        if self.request.user.role == User.Role.CUSTOMER:
            return ["title", "description", "category", "priority"]
        return [
            "title",
            "description",
            "category",
            "priority",
            "status",
            "assigned_to",
            "due_date",
        ]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.CUSTOMER:
            qs = qs.filter(status=Ticket.Status.NEW)
        return qs

    def form_valid(self, form):
        old_status = Ticket.objects.get(pk=self.object.pk).status
        response = super().form_valid(form)
        if old_status != self.object.status:
            TicketHistory.objects.create(
                ticket=self.object,
                user=self.request.user,
                action="Đổi trạng thái",
                old_value=old_status,
                new_value=self.object.status,
            )
        return response


class TicketDeleteView(LoginRequiredMixin, TicketQuerysetMixin, DeleteView):
    model = Ticket
    success_url = reverse_lazy("tickets:list")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == User.Role.CUSTOMER:
            qs = qs.filter(status=Ticket.Status.NEW)
        return qs


class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        content = request.POST.get("content", "").strip()
        is_internal = (
            request.POST.get("is_internal") == "on"
            and request.user.role != User.Role.CUSTOMER
        )

        if content:
            comment = Comment.objects.create(
                ticket=ticket,
                user=request.user,
                content=content,
                is_internal=is_internal,
            )
            file = request.FILES.get("attachment")
            if file:
                Attachment.objects.create(
                    ticket=ticket, comment=comment, uploaded_by=request.user, file=file
                )
            TicketHistory.objects.create(
                ticket=ticket,
                user=request.user,
                action="Thêm bình luận" + (" (Nội bộ)" if is_internal else ""),
            )
        return redirect("tickets:detail", pk=ticket.pk)

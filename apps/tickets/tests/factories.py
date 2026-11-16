import factory

from apps.accounts.models import User
from apps.tickets.models import Category, Comment, Priority, Ticket


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    role = User.Role.CUSTOMER


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: f"Danh mục {n}")
    description = "Mô tả danh mục hỗ trợ"


class PriorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Priority
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: f"Mức ưu tiên {n}")
    level_weight = 1
    color = "#64748b"


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Faker("sentence", nb_words=5, locale="vi_VN")
    description = factory.Faker("paragraph", locale="vi_VN")
    status = Ticket.Status.NEW
    category = factory.SubFactory(CategoryFactory)
    priority = factory.SubFactory(PriorityFactory)
    customer = factory.SubFactory(UserFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    ticket = factory.SubFactory(TicketFactory)
    user = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence", nb_words=10, locale="vi_VN")
    is_internal = False

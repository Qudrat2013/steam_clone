from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Group, GroupMembership, GroupPost, GroupPostComment, GroupChatMessage
from .forms import GroupCreateForm, GroupPostForm, GroupChatMessageForm


def group_list(request):
    query = request.GET.get('q', '')
    groups = Group.objects.filter(is_public=True)
    if query:
        groups = groups.filter(Q(name__icontains=query) | Q(tag__icontains=query))

    paginator = Paginator(groups, 12)
    page = request.GET.get('page')
    groups = paginator.get_page(page)

    return render(request, 'groups/group_list.html', {'groups': groups, 'query': query})


@login_required
def group_create(request):
    if request.method == 'POST':
        form = GroupCreateForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()
            GroupMembership.objects.create(group=group, user=request.user, role='owner', status='approved')
            messages.success(request, f'Группа «{group.name}» создана!')
            return redirect('groups:detail', pk=group.pk)
    else:
        form = GroupCreateForm()
    return render(request, 'groups/group_create.html', {'form': form})


def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)
    membership = None
    if request.user.is_authenticated:
        membership = GroupMembership.objects.filter(group=group, user=request.user).first()

    posts = group.posts.all()[:10]
    members = group.memberships.filter(status='approved').select_related('user')[:20]

    return render(request, 'groups/group_detail.html', {
        'group': group,
        'membership': membership,
        'posts': posts,
        'members': members,
    })


@login_required
def group_join(request, pk):
    group = get_object_or_404(Group, pk=pk)
    membership, created = GroupMembership.objects.get_or_create(
        group=group, user=request.user,
        defaults={'status': 'approved', 'role': 'member'}
    )
    if created:
        messages.success(request, f'Вы вступили в группу «{group.name}»!')
    elif membership.status == 'banned':
        messages.error(request, 'Вы заблокированы в этой группе.')
    else:
        messages.info(request, 'Вы уже в этой группе.')
    return redirect('groups:detail', pk=pk)


@login_required
def group_leave(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if group.owner == request.user:
        messages.error(request, 'Владелец не может покинуть группу.')
        return redirect('groups:detail', pk=pk)
    GroupMembership.objects.filter(group=group, user=request.user).delete()
    messages.success(request, f'Вы покинули группу «{group.name}».')
    return redirect('groups:list')


@login_required
def group_forum(request, pk):
    group = get_object_or_404(Group, pk=pk)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')

    posts = group.posts.all()
    paginator = Paginator(posts, 15)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    post_form = GroupPostForm()
    return render(request, 'groups/group_forum.html', {
        'group': group, 'posts': posts, 'post_form': post_form, 'membership': membership
    })


@login_required
def group_post_create(request, pk):
    group = get_object_or_404(Group, pk=pk)
    get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')

    if request.method == 'POST':
        form = GroupPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.group = group
            post.author = request.user
            post.save()
            messages.success(request, 'Пост создан!')
            return redirect('groups:post_detail', pk=pk, post_pk=post.pk)
    return redirect('groups:forum', pk=pk)


@login_required
def group_post_detail(request, pk, post_pk):
    group = get_object_or_404(Group, pk=pk)
    post = get_object_or_404(GroupPost, pk=post_pk, group=group)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')

    comments = post.comments.all()

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            GroupPostComment.objects.create(post=post, author=request.user, content=content)
            return redirect('groups:post_detail', pk=pk, post_pk=post_pk)

    return render(request, 'groups/group_post_detail.html', {
        'group': group, 'post': post, 'comments': comments, 'membership': membership
    })


@login_required
def group_chat(request, pk):
    group = get_object_or_404(Group, pk=pk)
    get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')
    messages_qs = group.chat_messages.select_related('author').order_by('-created_at')[:50]
    return render(request, 'groups/group_chat.html', {
        'group': group,
        'chat_messages': reversed(list(messages_qs)),
    })


@login_required
def group_chat_send(request, pk):
    """AJAX endpoint for sending chat messages."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    group = get_object_or_404(Group, pk=pk)
    get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')

    content = request.POST.get('content', '').strip()
    if not content or len(content) > 500:
        return JsonResponse({'error': 'Некорректное сообщение'}, status=400)

    msg = GroupChatMessage.objects.create(group=group, author=request.user, content=content)
    return JsonResponse({
        'id': msg.id,
        'author': msg.author.username,
        'content': msg.content,
        'created_at': msg.created_at.strftime('%H:%M'),
    })


@login_required
def group_chat_messages(request, pk):
    """AJAX polling for new messages."""
    group = get_object_or_404(Group, pk=pk)
    get_object_or_404(GroupMembership, group=group, user=request.user, status='approved')

    last_id = request.GET.get('last_id', 0)
    msgs = group.chat_messages.filter(id__gt=last_id).select_related('author').order_by('created_at')

    data = [{
        'id': m.id,
        'author': m.author.username,
        'content': m.content,
        'created_at': m.created_at.strftime('%H:%M'),
        'is_me': m.author == request.user,
    } for m in msgs]

    return JsonResponse({'messages': data})
from django.template import RequestContext
# from django.shortcuts import render_to_response
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from taggit.models import Tag
from blog.forms import CommentForm, EmailPostForm
from .models import Post
from django.core.paginator import Paginator, EmptyPage,PageNotAnInteger
from django.views.generic import ListView
from django.core.mail import send_mail
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .forms import EmailPostForm, CommentForm, PostForm, SearchForm
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.auth.decorators import login_required


def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
    paginator = Paginator(object_list, 3) # get three posts per page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    return render(request, 'blog/post/list.html', {'page':page,'posts': posts, 'tag':tag})
    pass

class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, status='published', publish__year=year, publish__month=month, publish__day=day, slug=post)
    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    # List of active comments for this post
    comments = post.comments.filter(active=True)
    new_comment = None
    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Create Comment object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # Assign the current post to the comment
            new_comment.post = post
            # Save the comment to the database
            new_comment.save()
    else:
        comment_form = CommentForm()
    return render(request,
                'blog/post/detail.html',{'post': post,'comments': comments,'new_comment': new_comment,'comment_form': comment_form,
                                         'similar_posts': similar_posts})


def share_post(request, post_id):
    # retrieve the post by post_id
    post = get_object_or_404(Post, id=post_id, status='published')

    if request.method == 'POST':
        #Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{}({}) recommends you reading "{}"'.format(cd['name'], cd['email'], post.title)
            message= 'Read "{}" at {}\n\n{}\'s comments:{}'.format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'admin@myblog.com',
                        [cd['to']])
            sent=True

    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.status = 'published'
            new_post.author = request.user
            new_post.save()
            form.save_m2m()
            return redirect(reverse('blog:post_list'))
    else:
        form = PostForm()
    return render(request, 'blog/post/create_post.html', {'form': form})
        



def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A') + SearchVector('body',
                                                                             weight='B')
            search_query = SearchQuery(query)
            results = Post.objects.annotate(
                search=search_query, rank=SearchRank(search_vector, search_query)
            ).filter(rank__gte=0.3).order_by('-rank')
    return render(request,
                'blog/post/search.html',
                {'form': form,
                'query': query,
                'results': results})


def handler404(request, *args, **argv):
    return render(request, '404.html', {})


def handler500(request, *args, **argv):
    return render(request, '500.html', {})

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from taggit.managers import TaggableManager
from django.utils.text import slugify

class PublishedManager(models.Manager):
    def get_queryset(self):
        return super(PublishedManager,
                self).get_queryset().filter(status='published')

class Post(models.Model):
    STATUS_CHOICES=(
        ('draft', 'Darft'),
        ('published', 'Published')
    )   
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=250)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    body = models.TextField()
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,
                              choices=STATUS_CHOICES,
                              default='draft')
    objects = models.Manager()  # The default manager.
    published = PublishedManager()  # Our custom manager.
    tags = TaggableManager()

    class Meta:
        ordering = ('-publish',)
        
        
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('blog:post_detail',
               args=[self.publish.year,
                     self.publish.month,
                     self.publish.day,
                     self.slug])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Post, self).save(*args, **kwargs)

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE ,related_name='comments')
    name = models.CharField(max_length=80)
    email = models.EmailField()
    body = models.TextField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ('created',)

    def __str__(self):
        return f"Comment by {self.name} on {self.post}"

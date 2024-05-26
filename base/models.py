from django.db import models
from django.contrib.auth.models import User

class BookTitle(models.Model):
    isbn = models.CharField(max_length=13, unique=True, primary_key=True)
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    cover_url = models.URLField(null=True, blank=True)
    
    def __str__(self):
        return self.isbn + " - " + self.title
  

class BookCopy(models.Model):
    book_title = models.ForeignKey(BookTitle, on_delete=models.CASCADE)
    library_branch_id = models.IntegerField()
    year = models.IntegerField()
    is_available = models.BooleanField(default=True)
    is_reserved = models.BooleanField(default=False)
    is_reservasion_ready = models.BooleanField(default=False)
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date_of_return = models.DateField(null=True, blank=True) 
    
    class Meta:
        ordering = ['library_branch_id', '-year']

    def __str__(self):
        return self.book_title.title + " - " + self.id.__str__()
  

class PromotionRow(models.Model):
    title = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    

class PromotionRowsLogs(models.Model):
    promotion_row_id = models.ForeignKey(PromotionRow, on_delete=models.CASCADE)
    book_title = models.ForeignKey(BookTitle, on_delete=models.CASCADE)

    def __str__(self):
        return self.promotion_row_id.title + " - " + self.book_title.title
    

class FavouritesLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book_title = models.ForeignKey(BookTitle, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'book_title')
        ordering = ['book_title']

    def __str__(self):
        return self.user.username + " - " + self.book_title.title
  
class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fines = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return self.user.username + " - " + self.fines.__str__()
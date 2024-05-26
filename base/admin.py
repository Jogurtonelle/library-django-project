from django.contrib import admin

# Register your models here.
from .models import BookTitle
from .models import BookCopy
from .models import PromotionRow
from .models import PromotionRowsLogs
from .models import FavouritesLog


admin.site.register(FavouritesLog)
admin.site.register(BookTitle)
admin.site.register(BookCopy)
admin.site.register(PromotionRow)
admin.site.register(PromotionRowsLogs)
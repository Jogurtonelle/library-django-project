from decimal import Decimal
import random
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth import logout, login, authenticate
import datetime
from datetime import timedelta
from libraryapp import settings
from .models import BookTitle, BookCopy, PromotionRow, PromotionRowsLogs, FavouritesLog, UserDetails
from django.contrib.auth.models import User
from django.contrib import messages
import stripe

def home(request):
    # Get all active promotion rows
    promotion_rows = PromotionRow.objects.filter(is_active=True)
    promotion_rows_logs = PromotionRowsLogs.objects.filter(promotion_row_id__in=promotion_rows)

    data = {}
    for row in promotion_rows:
        data[row.title] = []
        for log in promotion_rows_logs.filter(promotion_row_id=row):
            data[row.title].append(log.book_title)

    return render(request, 'home.html', {"data": data})

def book(request, isbn):
    try:
        book = BookTitle.objects.get(isbn=isbn)
        book_copies = BookCopy.objects.filter(book_title=book)

        branches = set()
        for copy in book_copies:
            branches.add(copy.library_branch_id)

        is_favourite = False
        favourites = None

        if request.user.is_authenticated:
            favourites = FavouritesLog.objects.filter(user=request.user, book_title=book)
            is_favourite = False
            if favourites.exists():
                is_favourite = True

        return render(request, 'book.html', {"book_title": book, "book_copies": book_copies, "is_favourite": is_favourite, "branches": branches})
    except BookTitle.DoesNotExist:
        return HttpResponse("Book not found")

def search(request):
    search_query = request.GET.get('search')

    # If search query is empty, redirect to home
    if search_query is None or search_query == "":
        return redirect('home')
    
    # If search query is an ISBN, redirect to book page if book with such ISBN exists
    if len(search_query) == 13 and search_query.isdigit():
        book = BookTitle.objects.filter(isbn=search_query)
        if book.exists():
            return redirect('book', isbn=search_query)
        else:
            return HttpResponse("Book not found")
        
    # Search for books by title or author
    books = BookTitle.objects.filter(
        Q(title__icontains=search_query) |
        Q(author__icontains=search_query)
    )[:15]

    # If only one book is found, redirect to book page
    if len(books) == 1:
        return redirect('book', isbn=books[0].isbn)

    # finally, render search results
    return render(request, 'searchResults.html', {"books": books})

def profile(request):
    try:
        session_id = request.GET.get('session_id')
        stripe.api_key = settings.STRIPE_SECRET_KEY
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status == 'paid':
            print("Payment successful")
            user_detail = UserDetails.objects.get(user=request.user)
            user_detail.fines = 0
            user_detail.save()
    except:
        HttpResponse("Payment failed")

    favoutites = FavouritesLog.objects.filter(user=request.user)

    book_copies = BookCopy.objects.filter(borrower=request.user)
    borrowed_books = book_copies.filter(is_reserved=False)
    reserved_books_ready = book_copies.filter(is_reserved=True, is_reservasion_ready=True)
    reserved_books_not_ready = book_copies.filter(is_reserved=True, is_reservasion_ready=False)

    try:
        fines = UserDetails.objects.get(user=request.user).fines
    except UserDetails.DoesNotExist:
        UserDetails.objects.create(user=request.user, fines=0)
        fines = 0

    if fines >= 2:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'blik', 'p24'],
            line_items=[{
                'price': 'price_1PICxbDObNsoznhDFZEMHXYc',
                'quantity': int(fines * 10),
            }], 
            mode='payment',
            success_url='http://127.0.0.1:8000/profile/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/profile/'
        )
        return render(request, 'profile.html', {"favourites": favoutites, "borrowed_books": borrowed_books, "reserved_books_ready": reserved_books_ready, "reserved_books_not_ready": reserved_books_not_ready, "fines": fines, "session_id": session.id, "stripe_public_key": settings.STRIPE_PUBLIC_KEY})

    return render(request, 'profile.html', {"favourites": favoutites, "borrowed_books": borrowed_books, "reserved_books_ready": reserved_books_ready, "reserved_books_not_ready": reserved_books_not_ready, "fines": fines})

def payFine(request):
    if request.user.is_authenticated:
        try:
            fine = UserDetails.objects.get(user=request.user)
            if fine.fines > 0:
                
                return redirect('profile')
            else:
                return HttpResponse("No fines to pay")
        except UserDetails.DoesNotExist:
            return HttpResponse("User not found or no fines to pay")

def manageFavourites(request):
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        action = request.POST.get('action')

        try:
            book = BookTitle.objects.get(isbn=isbn)
        except BookTitle.DoesNotExist:
            return HttpResponse("Book not found")
        
        if action == 'remove':
            favlog = FavouritesLog.objects.filter(user=request.user, book_title=book)
            if favlog.exists():
                favlog.delete()
        else:
            favlog = FavouritesLog.objects.filter(user=request.user, book_title=book)
            if not favlog.exists():
                FavouritesLog.objects.create(user=request.user, book_title=book)

        return redirect(request.META.get('HTTP_REFERER'))
    else:
        return HttpResponse("Method not allowed")

def reserve(request):
    if request.method == 'POST':
        id_ = request.POST.get('book_copy_id')
        try:
            book_copy = BookCopy.objects.get(id=id_, is_available=True)
            book_copy.is_available = False
            book_copy.borrower = request.user
            book_copy.is_reserved = True
            book_copy.is_reservasion_ready = False
            book_copy.date_of_return = (datetime.datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            book_copy.save()
            return redirect(request.META.get('HTTP_REFERER'))
        except BookCopy.DoesNotExist:
            return HttpResponse("Book copy not found")
    else:
        book_copy = BookCopy(
            book_title=BookTitle.objects.get(isbn=request.GET.get('isbn')),
            library_branch_id=request.GET.get('library_branch_id'),
            year=request.GET.get('year')
        )

def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Użytkownik nie istnieje.')
            return redirect('login')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.add_message(request, messages.ERROR, 'Nieprawidłowe hasło.')
            return redirect('login')
        
    else:
        return render(request, 'login.html')

def logoutUser(request):
    logout(request)
    return redirect('home')

# dont use this in production
def init(request):
    book_titles = BookTitle.objects.all()

    for book in book_titles:
        if BookCopy.objects.filter(book_title=book).exists():
            continue
        for i in range(0, random.randint(1, 5)):
            BookCopy.objects.create(
                book_title=book,
                library_branch_id = random.randint(0, 5),
                year = random.randint(2000, 2020)
            )

def myadmin(request):
    if request.user.is_staff:
        return render(request, 'myadmin.html')
    
def myadmin_adduser(request):
    if request.user.is_staff:
        if request.method == 'POST':
            name = request.POST.get('name')
            surname = request.POST.get('surname')
            email = request.POST.get('email')
            card = request.POST.get('card')

            if User.objects.filter(username=card).exists():
                messages.add_message(request, messages.ERROR, 'Card number already exists')
                return redirect('myadmin_adduser')
            elif User.objects.filter(email=email).exists():
                messages.add_message(request, messages.ERROR, 'Email already exists')
                return redirect('myadmin_adduser')
            elif len(card) != 11:
                messages.add_message(request, messages.ERROR, 'Card number must be 11 characters long')
                return redirect('myadmin_adduser')
            

            role = request.POST.get('role')

            if role == 'admin':
                is_staff = True
                is_superuser = True
            else:
                is_staff = False
                is_superuser = False

            user = User.objects.create_user(
                username = card,
                password = card,
                is_staff = is_staff,
                is_superuser = is_superuser,
                first_name = name,
                last_name = surname,
                email = email
            )
            user.save()
            return redirect('myadmin')
        else:
            return render(request, 'myadmin_adduser.html')
    else:
        return HttpResponse("Access denied")
            
def myadmin_addbook(request):
    if request.user.is_staff:
        if request.method == 'POST':
            isbn = request.POST.get('isbn')
            title = request.POST.get('title')
            author = request.POST.get('author')
            description = request.POST.get('description')
            cover_url = request.POST.get('cover_url')

            if BookTitle.objects.filter(isbn=isbn).exists():
                messages.add_message(request, messages.ERROR, 'Book with this ISBN already exists')
                return redirect('myadmin_addbook')
            elif len(isbn) != 13:
                messages.add_message(request, messages.ERROR, 'ISBN must be 13 characters long')
                return redirect('myadmin_addbook')

            book = BookTitle.objects.create(
                isbn = isbn,
                title = title,
                author = author,
                description = description,
                cover_url = cover_url
            )
            book.save()
            return redirect('myadmin')
        else:
            return render(request, 'myadmin_addbook.html')
    else:
        return HttpResponse("Access denied")
    
def myadmin_addcopy(request):
    if request.user.is_staff:
        if request.method == 'POST':
            isbn = request.POST.get('isbn')
            library_branch_id = request.POST.get('library_branch_id')
            year = request.POST.get('year')

            book = None
            try:
                book = BookTitle.objects.get(isbn=isbn)
            except BookTitle.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Book with this ISBN does not exist')
                return redirect('myadmin_addcopy')

            book_copy = BookCopy.objects.create(
                book_title = book,
                library_branch_id = library_branch_id,
                year = year
            )
            book_copy.save()
            return redirect('myadmin')
        else:
            return render(request, 'myadmin_addcopy.html')
    else:
        return HttpResponse("Access denied")

def myadmin_getuser(request):
    if request.user.is_staff:
        return render(request, 'myadmin_getuser.html')
    else:
        return HttpResponse("Access denied")

def myadmin_manageuser(request, card_user):
    if request.user.is_staff:
        if card_user is None:
            card = request.POST.get('user_card')
        else:
            card = card_user

        try:
            user_card = User.objects.get(username=card)
        except User.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'User not found')
            return redirect('myadmin_manageuser')
        
        books = BookCopy.objects.filter(borrower=User.objects.get(username=user_card))
        borrowed_books = books.filter(is_reserved=False)
        reserved_books_ready = books.filter(is_reserved=True, is_reservasion_ready=True)
        reserved_books_not_ready = books.filter(is_reserved=True, is_reservasion_ready=False)
        #print(books, borrowed_books, reserved_books_ready, reserved_books_not_ready)
        return render(request, 'myadmin_manageuser.html', {"user_card": user_card, "borrowed_books": borrowed_books, "reserved_books_ready": reserved_books_ready, "reserved_books_not_ready": reserved_books_not_ready})
    
    else:
        return HttpResponse("Access denied")

#Post only
def myadmin_returnbook(request):
    if request.user.is_staff:
        if request.method == 'POST':
            book_copy_id = request.POST.get('book_id')
            user_card = request.POST.get('user_card')
            try:
                book_copy = BookCopy.objects.get(id=book_copy_id)
            except BookCopy.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Book copy not found')
                return redirect(request.META.get('HTTP_REFERER'))
            
            #check duration beetween now and date_of_return
            if book_copy.date_of_return < datetime.date.today():
                #print ((datetime.date.today() - book_copy.date_of_return).days)
                try:
                    fine = UserDetails.objects.get(user=User.objects.get(username=user_card))
                    fine.fines += ((datetime.date.today() - book_copy.date_of_return).days) * Decimal(0.10)
                    fine.save()
                except UserDetails.DoesNotExist:
                    fine = UserDetails.objects.create(user=User.objects.get(username=user_card), fines=((datetime.date.today() - book_copy.date_of_return).days) * Decimal(0.10))

                                                      
            book_copy.is_available = True
            book_copy.borrower = None
            book_copy.date_of_return = None
            book_copy.save()

            return redirect(request.META.get('HTTP_REFERER'))
    else:
        return HttpResponse("Access denied")

#Post only
def myadmin_cancelreservation(request):
    if request.method == 'POST':
        book_copy_id = request.POST.get('book_id')
        user_card = request.POST.get('user_card')
        try:
            book_copy = BookCopy.objects.get(id=book_copy_id)
        except BookCopy.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Book copy not found')
            return redirect(request.META.get('HTTP_REFERER'))
        
        book_copy.is_available = True
        book_copy.is_reserved = False
        book_copy.is_reservasion_ready = False
        book_copy.borrower = None
        book_copy.date_of_return = None
        book_copy.save()

        return redirect(request.META.get('HTTP_REFERER'))
    else:
        return HttpResponse("Method not allowed")

#Post only
def myadmin_reservationready(request):
    if request.user.is_staff:
        if request.method == 'POST':
            book_copy_id = request.POST.get('book_id')
            try:
                book_copy = BookCopy.objects.get(id=book_copy_id)
            except BookCopy.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Book copy not found')
                return redirect(request.META.get('HTTP_REFERER'))
            
            book_copy.is_available = False
            book_copy.is_reservasion_ready = True
            book_copy.is_reserved = True
            book_copy.save()

            return redirect(request.META.get('HTTP_REFERER'))
        else:
            return HttpResponse("Method not allowed")
    else:
        return HttpResponse("Access denied")

def myadmin_bookborrowed(request):
    if request.user.is_staff:
        if request.method == 'POST':
            book_copy_id = request.POST.get('book_id')
            try:
                book_copy = BookCopy.objects.get(id=book_copy_id)
            except BookCopy.DoesNotExist:
                messages.add_message(request, messages.ERROR, 'Book copy not found')
                return redirect(request.META.get('HTTP_REFERER'))
            
            book_copy.is_available = False
            book_copy.is_reservasion_ready = False
            book_copy.is_reserved = False
            book_copy.save()

            return redirect(request.META.get('HTTP_REFERER'))
        else:
            return HttpResponse("Method not allowed")
    else:
        return HttpResponse("Access denied")

def myadmin_reservations(request):
    if request.user.is_staff:
        books = BookCopy.objects.filter(is_reserved=True)
        reserved_books_ready = books.filter(is_reserved=True, is_reservasion_ready=True)
        reserved_books_not_ready = books.filter(is_reserved=True, is_reservasion_ready=False)
        return render(request, 'myadmin_reservations.html', {"reserved_books_ready": reserved_books_ready, "reserved_books_not_ready": reserved_books_not_ready})
    else:
        return HttpResponse("Access denied")

def myadmin_promotions(request):
    if request.user.is_staff:
        if request.method == 'POST':
            match request.POST.get('action'):
                case 'activate':
                    row_name = request.POST.get('row_name')
                    row = PromotionRow.objects.get(title=row_name)
                    row.is_active = True
                    row.save()
                    return redirect('myadmin_promotions')
                case 'deactivate':
                    row_name = request.POST.get('row_name')
                    row = PromotionRow.objects.get(title=row_name)
                    row.is_active = False
                    row.save()
                    return redirect('myadmin_promotions')
                case 'add_row':
                    row_name = request.POST.get('row_name')
                    if PromotionRow.objects.filter(title=row_name).exists():
                        messages.add_message(request, messages.ERROR, 'Promotion row with this name already exists')
                        return redirect('myadmin_promotions')
                    row = PromotionRow.objects.create(title=row_name, is_active=False)
                    row.save()
                    return redirect('myadmin_promotions')
                case 'remove_book':
                    row_name = request.POST.get('row_name')
                    book_isbn = request.POST.get('book_isbn')
                    print (row_name, book_isbn)
                    try:
                        row = PromotionRow.objects.get(title=row_name)
                        book = BookTitle.objects.get(isbn=book_isbn)
                        log = PromotionRowsLogs.objects.get(promotion_row_id=row, book_title=book)
                        log.delete()
                        return redirect('myadmin_promotions')
                    except PromotionRow.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Promotion row not found')
                        return redirect('myadmin_promotions')
                    except BookTitle.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Book not found')
                        return redirect('myadmin_promotions')
                    except PromotionRowsLogs.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Book not found in promotion row')
                        return redirect('myadmin_promotions')
                case 'remove_row':
                    row_name = request.POST.get('row_name')
                    try:
                        row = PromotionRow.objects.get(title=row_name)
                        row.delete()
                        return redirect('myadmin_promotions')
                    except PromotionRow.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Promotion row not found')
                        return redirect('myadmin_promotions')
                case 'add_book':
                    row_name = request.POST.get('row_name')
                    book_isbn = request.POST.get('book_isbn')
                    try:
                        row = PromotionRow.objects.get(title=row_name)
                        book = BookTitle.objects.get(isbn=book_isbn)

                        if PromotionRowsLogs.objects.filter(promotion_row_id=row, book_title=book).exists():
                            messages.add_message(request, messages.ERROR, 'Book already in promotion row')
                            return redirect('myadmin_promotions')
                        
                        log = PromotionRowsLogs.objects.create(promotion_row_id=row, book_title=book)
                        log.save()
                        return redirect('myadmin_promotions')
                    except PromotionRow.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Promotion row not found')
                        return redirect('myadmin_promotions')
                    except BookTitle.DoesNotExist:
                        messages.add_message(request, messages.ERROR, 'Book not found')
                        return redirect('myadmin_promotions')
        else:
            promotionrows = PromotionRow.objects.all()
            promotionrowslogs = PromotionRowsLogs.objects.all()

            data = {}
            for row in promotionrows:
                data[row] = []
                for log in promotionrowslogs.filter(promotion_row_id=row):
                    data[row].append(log.book_title)
                    
            return render(request, 'myadmin_promotions.html', {"data": data})

def changePassword(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password_confirm = request.POST.get('new_password2')

        user = authenticate(request, username=request.user.username, password=old_password)

        if user is not None:
            if new_password != new_password_confirm:
                messages.add_message(request, messages.ERROR, 'Nowe hasła nie są takie same.')
                return redirect('change-password')
            if len(new_password) < 8:
                messages.add_message(request, messages.ERROR, 'Nowe hasło jest za krótkie - conajmniej 8 znaków.')
                return redirect('change-password')
            user.set_password(new_password)
            user.save()
            return redirect('home')
        else:
            messages.add_message(request, messages.ERROR, 'Nieprawidłowe hasło.')
            return redirect('change-password')
    else:
        return render(request, 'change_password.html')
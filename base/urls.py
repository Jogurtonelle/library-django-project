from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('reserve/', views.reserve, name="reserve"), #POST ONLY
    path('book/<str:isbn>/', views.book, name="book"),
    path('profile/', views.profile, name="profile"),
    path('search/', views.search, name="search"),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('manage-favs/', views.manageFavourites, name="manage-favs"), #POST ONLY
    path('myadmin/', views.myadmin, name="myadmin"),
    path('myadmin/adduser/', views.myadmin_adduser, name="myadmin_adduser"),
    path('myadmin/addbook/', views.myadmin_addbook, name="myadmin_addbook"),
    path('myadmin/addcopy/', views.myadmin_addcopy, name="myadmin_addcopy"),
    path('myadmin/getuser/', views.myadmin_getuser, name="myadmin_getuser"),
    path('myadmin/manageuser/<str:card_user>', views.myadmin_manageuser, name="myadmin_manageuser"),
    path('myadmin/returnbook/', views.myadmin_returnbook, name="myadmin_returnbook"), #POST ONLY
    path('myadmin/cancelreservation/', views.myadmin_cancelreservation, name="myadmin_cancelreservation"), #POST ONLY
    path('myadmin/reservations/', views.myadmin_reservations, name="myadmin_reservations"),
    path('myadmin/reservationready/', views.myadmin_reservationready, name="myadmin_reservationready"), #POST ONLY
    path('myadmin/bookborrowed/', views.myadmin_bookborrowed, name="myadmin_bookborrowed"), #POST ONLY
    path('myadmin/promotions/', views.myadmin_promotions, name="myadmin_promotions"),
    path('change-password/', views.changePassword, name="change-password"),
    path('init/', views.init, name="init"),
]


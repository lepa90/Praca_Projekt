
from rest_framework import routers
from django.conf.urls import url, include
from django.contrib.auth.views import LoginView, LogoutView
from .views import HomeView, PlaceViewSet, BookingViewSet, BookingList, BookingAdd, BookingEdit, PlaceList, PlaceAdd,\
    PlaceEdit, SearchViewSet, BookingSearch, register


app_name = 'ideass'
router = routers.DefaultRouter()
router.register('places', PlaceViewSet)
router.register('bookings', BookingViewSet)
router.register('search', SearchViewSet, basename='search')

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^login/', LoginView.as_view(), name='login'),
    url(r'^logout/', LogoutView.as_view(), name='logout'),
    url(r'^register/', register, name="register"),
    url(r'^book/$', BookingAdd.as_view(), name="book"),
    url(r'^bookings/$', BookingList.as_view(), name='bookings'),
    url(r'^bookings/(?P<pk>[0-9]+)/$', BookingEdit.as_view()),
    url(r'^place_add/$', PlaceAdd.as_view(), name='place_add'),
    url(r'^place/$', PlaceList.as_view(), name='places'),
    url(r'^places/(?P<number>[0-9]+)/$', PlaceEdit.as_view()),
    url(r'^search/$', BookingSearch.as_view(), name='search'),
    url(r'^place_edit/$', PlaceEdit.as_view(), name='place_edit'),
]



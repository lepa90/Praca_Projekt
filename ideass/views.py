
from datetime import datetime
from json import dumps
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect
from rest_framework import viewsets, status
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.generics import GenericAPIView
from drf_yasg.utils import swagger_auto_schema
from .models import Place, Booking
from .serializers import PlaceSerializer, BookingSerializer, SearchBookingSerializer
from .permissions import HasGroupPermission, REQ_GROUPS_BOOKINGS, REQ_GROUPS_BOOKINGS_UPDATE, REQ_GROUPS_PLACE
from .forms import SignUpForm
from .config import PLACE_PRICES
from aktualneprojektkamil.settings import REGISTRATION_OPEN

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %%%%%%%%%%%%%%%%%%%%%%%%% API VIEWS %%%%%%%%%%%%%%%%%%%%%%%%%%
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
class PlaceViewSet(viewsets.ModelViewSet):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    http_method_names = ['get', 'post', 'head', 'put', 'delete']
    permission_classes = (HasGroupPermission,)
    required_groups = REQ_GROUPS_PLACE
    template_name = 'bookings.html'
    # place duplication is prevented by RoomSerializer internally with is_valid()

    def destroy(self, request, *args, **kwargs):  # DELETE
        instance = get_object_or_404(Place, number=kwargs['pk'])  # pk is just place number from url
        if Booking.objects.filter(places=instance).exists():
            return Response({'error': 'This place is used by at least one booking, cannot be deleted'},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    http_method_names = ['get', 'post', 'head', 'put', 'delete']
    permission_classes = (HasGroupPermission,)
    required_groups = REQ_GROUPS_BOOKINGS

    def create(self, request, *args, **kwargs):  # POST
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return super().create(request, *args, **kwargs)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):  # PUT
        instance = self.get_object()
        serializer = BookingSerializer(instance=instance, data=request.data, context={'request': request})
        if serializer.is_valid():
            return super().update(request, *args, **kwargs)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SearchViewSet(GenericViewSet, ListModelMixin):
    serializer_class = SearchBookingSerializer
    http_method_names = ['get']
    permission_classes = (HasGroupPermission,)
    required_groups = {'GET': ['Staff']}

    def get_queryset(self):
        queryset = Booking.objects.all()
        params = self.request.query_params.copy().dict()
        params = {key: value for key, value in params.items() if value != ''}
        if 'places' in params.keys():
            places = params['places'].split(',')
            for place in places:
                queryset = queryset.filter(places=place).distinct()
            del params['places']
        if 'created' in params.keys():
            created = datetime.strptime(params['created'], '%Y-%m-%d')
            queryset = queryset.filter(created__date=created).distinct()
            del params['created']
        queryset = queryset.filter(**params).distinct()
        return queryset

    @swagger_auto_schema(query_serializer=SearchBookingSerializer)  # just to fix schemas in swagger
    def list(self, request, *args, **kwargs):
        serializer = SearchBookingSerializer(data=self.request.data, context={'request': self.request})
        if serializer.is_valid():
            return super().list(self)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# %%%%%%%%%%%%%%%%%%%%%%% FRONTEND VIEWS %%%%%%%%%%%%%%%%%%%%%%%
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

class HomeView(TemplateView):
    template_name = 'home.html'

def register(request):  # FBV just once for simplicity here
    context = {}
    form = SignUpForm(request.POST or None)
    if request.method == "POST":
        if REGISTRATION_OPEN is False:
            messages.warning(request, f'Registrations are currently disabled!')
            return render(request, 'home.html')
        else:
            if form.is_valid():
                user = form.save()
                login(request, user)
                messages.success(request, f'Registered successfully!')
                return render(request, 'home.html')
    context['form'] = form
    context['REGISTRATION_OPEN'] = REGISTRATION_OPEN
    return render(request, 'registration/register.html', context)


class RoomGenericAPIView(GenericAPIView):
    schema = None  # to hide non-api views from swagger
    style = {'template_pack': 'rest_framework/vertical/'}
    renderer_classes = [TemplateHTMLRenderer]
    base_viewset = PlaceViewSet
    permission_classes = base_viewset.permission_classes


class BookingGenericAPIView(GenericAPIView):
    schema = None  # to hide non-api views from swagger
    style = {'template_pack': 'rest_framework/vertical/'}
    renderer_classes = [TemplateHTMLRenderer]
    base_viewset = BookingViewSet
    permission_classes = base_viewset.permission_classes

class PlaceList(RoomGenericAPIView):
    template_name = 'places.html'
    required_groups = REQ_GROUPS_PLACE

    def get(self, request):
        queryset = Place.objects.all()
        return Response({'places': queryset})

class PlaceAdd(RoomGenericAPIView):
    template_name = 'place_add.html'
    required_groups = REQ_GROUPS_PLACE

    def get(self, request):
        serializer = PlaceSerializer
        return Response({'serializer': serializer, 'style': self.style})

    def post(self, request):
        serializer = RoomSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            messages.success(request, f'Place successfully added!')
            return redirect('/places/')
        return Response({'serializer': serializer, 'style': self.style})

class PlaceEdit(RoomGenericAPIView):
    template_name = 'place_edit.html'
    required_groups = REQ_GROUPS_PLACE

    def get(self, request, number):
        place = get_object_or_404(Room, number=number)
        serializer = PlaceSerializer(instance=room)
        return Response({'serializer': serializer, 'place': place, 'style': self.style})

    def post(self, request, number):  # HTML PUT and DELETE workaround
        method = request.POST.get("method", "")  # hidden input in forms, two buttons
        if method == 'PUT':
            return self.put(request, number)
        elif method == 'DELETE':
            instance = get_object_or_404(Room, number=number)
            place_number = instance.number
            if Booking.objects.filter(rooms=instance).exists():
                messages.warning(request, f'Place {place_number} is used by at least one booking and cannot be deleted!')
                return redirect('/places/')
            instance.delete()
            messages.success(request, f'Place {place_number} successfully deleted!')
            return redirect('/places/')
        messages.warning(request, f'Unknown method')
        return redirect('/places/')

    def put(self, request, number):
        instance = get_object_or_404(Place, number=number)
        serializer = PlaceSerializer(instance=instance, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            messages.success(request, f'Place {instance.number} successfully edited!')
            return redirect('/places/')
        return Response({'serializer': serializer, 'style': self.style})


class BookingList(BookingGenericAPIView):
    template_name = 'bookings.html'
    required_groups = REQ_GROUPS_BOOKINGS

    def get(self, request):
        queryset = Booking.objects.all()
        return Response({'bookings': queryset})


class BookingAdd(BookingGenericAPIView):
    template_name = 'book.html'
    required_groups = REQ_GROUPS_BOOKINGS

    def get(self, request):
        serializer = BookingSerializer
        return Response({'serializer': serializer, 'style': self.style, 'PLACE_PRICES': dumps(PLACE_PRICES)})

    def post(self, request):
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=self.request.user)
            messages.success(request, f'Booking successfully added!')
            return redirect('/bookings/')
        return Response({'serializer': serializer, 'style': self.style})

class BookingEdit(BookingGenericAPIView):
    template_name = 'booking_edit.html'
    required_groups = REQ_GROUPS_BOOKINGS_UPDATE

    def get(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        serializer = BookingSerializer(instance=booking)
        return Response({'serializer': serializer, 'booking': booking, 'style': self.style,
                         'PLACE_PRICES': dumps(PLACE_PRICES)})

    def post(self, request, pk):  # HTML PUT and DELETE workaround
        method = request.POST.get("method", "")  # hidden input in forms, two buttons
        if method == 'PUT':
            return self.put(request, pk)
        elif method == 'DELETE':
            instance = get_object_or_404(Booking, pk=pk)
            booking_id = instance.id
            instance.delete()
            messages.success(request, f'Booking {booking_id} successfully deleted!')
            return redirect('/bookings/')
        messages.warning(request, f'Unknown method')
        return redirect('/bookings/')

    def put(self, request, pk):
        instance = get_object_or_404(Booking, pk=pk)
        serializer = BookingSerializer(instance=instance, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            messages.success(request, f'Booking {instance.id} successfully edited!')
            return redirect('/bookings/')
        return Response({'serializer': serializer, 'style': self.style, 'PLACE_PRICES': dumps(PLACE_PRICES)})


class BookingSearch(BookingGenericAPIView):
    http_method_names = ['get']
    template_name = 'search.html'
    required_groups = REQ_GROUPS_BOOKINGS_UPDATE

    def get(self, request):
        if not request.query_params:
            bookings = Booking.objects.all()
            serializer = BookingSerializer
            return Response({'serializer': serializer, 'style': self.style, 'bookings': bookings})
        else:
            # this serializer is just for validation, not for rendering
            serializer = SearchBookingSerializer(data=self.request.data, context={'request': self.request})
            if serializer.is_valid():
                # reusing method from SearchViewSet
                bookings = SearchViewSet.get_queryset(self)
                serializer = BookingSerializer  # it has more fields that SearchBookingSerializer
                return Response({'serializer': serializer, 'style': self.style, 'bookings': bookings})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

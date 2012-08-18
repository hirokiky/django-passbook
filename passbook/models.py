# -*- coding: utf-8 -*-
import os

from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import simplejson as json
from django.contrib.sites.models import Site

IMAGE_PATH = os.path.join(settings.MEDIA_ROOT, 'passbook')
IMAGE_TYPE = '.*\.(png|PNG)$'
SITE_DOMAIN = Site.objects.get_current().domain


class Pass(models.Model):
    # Standard keys
    format_version = 1
    identifier = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=255)
    # identifier and serial number should be unique together.
    organization_name = models.CharField(max_length=255)
    team_identifier = models.CharField(max_length=255)
    # Brief description of the pass, used by the iOS accessibility technologies.
    # Don’t try to include all of the data on the pass in its description,
    # just include enough detail to distinguish passes of the same type.
    description = models.CharField(max_length=255)

    # Web service keys
    auth_token = models.CharField(max_length=255, blank=True, null=True)
    # webServiceURL string
    locations = models.ManyToManyField('Location', related_name='passes', blank=True, null=True)
    relevant_date = models.DateTimeField(blank=True, null=True)
    barcode = models.ForeignKey('Barcode', related_name='passes')
    background_color = models.CharField(max_length=20)
    foreground_color = models.CharField(max_length=20, blank=True, null=True)
    label_color = models.CharField(max_length=20, blank=True, null=True)

    # Images: background.png, icon.png, logo.png, thumbnail.png, strip.png
    IMAGE_KWARGS = {'path': IMAGE_PATH,
                    'recursive': True,
                    'match': IMAGE_TYPE,
                    'null': True,
                    'blank': True}

    logo = models.FilePathField('The image displayed on the front of the pass', **IMAGE_KWARGS)
    icon = models.FilePathField('The pass\'s icon', **IMAGE_KWARGS)
    thumbnail_image = models.FilePathField('An additional image displayed on the front of the pass', **IMAGE_KWARGS)
    background_image = models.FilePathField('The image displayed as the background of the front of the pass', **IMAGE_KWARGS)
    strip_image = models.FilePathField('The image displayed as a strip behind the primary fields on the front of the pass', **IMAGE_KWARGS)
    supress_strip_shine = models.NullBooleanField('Supress the shine effect of the strip image')
    logo_text = models.CharField(max_length=255, blank=True, null=True)

    """ Style-Specific Information Keys """
    PASS_TYPES = (('boardingPass', 'boarding pass'),
                  ('coupon', 'coupon'),
                  ('eventTicket', 'event ticket'),
                  ('storeCard', 'store card'),
                  ('generic', 'generic'),)

    type = models.CharField(max_length=50, choices=PASS_TYPES)
    header_fields = models.ManyToManyField('Field', related_name='header+', blank=True, null=True)
    primary_fields = models.ManyToManyField('Field', related_name='primary+')
    secondary_fields = models.ManyToManyField('Field', related_name='secondary+', blank=True, null=True)
    auxiliary_fields = models.ManyToManyField('Field', related_name='aux+', blank=True, null=True)
    back_fields = models.ManyToManyField('Field', related_name='back+', blank=True, null=True)

    # associatedStoreIdentifiers --> array of numbers --> where does it go?
    TRANSIT_TYPE_CHOICES = (('PKTransitTypeAir', 'air'),
                            ('PKTransitTypeTrain', 'train'),
                            ('PKTransitTypeBus', 'bus'),
                            ('PKTransitTypeBoat', 'boat'),
                            ('PKTransitTypeGeneric', 'generic'),)
    transit_type = models.CharField(max_length=20, choices=TRANSIT_TYPE_CHOICES, null=True, blank=True)  # Boarding pass only

    def serialize(self):
        data = {
            'formatVersion': self.format_version,
            'passTypeIdentifier': self.identifier,
            'serialNumber': self.serial_number,
            'teamIdentifier': self.team_identifier,
            'webServiceURL': 'https://%s%s' % (SITE_DOMAIN, reverse('passbook-webservice')),
            'barcode': self.barcode.serialize(),
            'organizationName': self.organization_name,
            'locations': [location.serialize() for location in self.locations.all()],
            self.type: {
                'headerFields': [field.serialize() for field in self.header_fields.all()],
                'primaryFields': [field.serialize() for field in self.primary_fields.all()],
                'secondaryFields': [field.serialize() for field in self.secondary_fields.all()],
                'backFields': [field.serialize() for field in self.back_fields.all()]
            }
        }
        return json.dumps(data)

    def __unicode__(self):
        return u'Pass %s - %s' % (self.identifier, self.serial_number)

    class Meta:
        verbose_name_plural = 'passes'


class Barcode(models.Model):
    FORMAT_CHOICES = (('PKBarcodeFormatPDF417', 'PDF 417'),
                      ('PKBarcodeFormatQR', 'QR'),
                      ('PKBarcodeFormatAztec', 'Aztec'),
                      ('PKBarcodeFormatText', 'Text'),)

    message = models.CharField(max_length=255)
    format = models.CharField('Barcode format', choices=FORMAT_CHOICES, max_length=50)
    encoding = models.CharField(max_length=50, default='iso-8859-1')
    alt_text = models.CharField(max_length=255, blank=True, null=True)

    def serialize(self):
        barcode = {
            'message': self.message,
            'format': self.format,
            'messageEncoding': self.encoding
        }
        if self.alt_text is not None:
            barcode['alternativeText'] = self.alt_text
        return barcode

    def __unicode__(self):
        return u'Barcode: %s' % self.message


class Field(models.Model):
    key = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    value = models.TextField()
    text_alignment = models.CharField(max_length=20, blank=True, null=True)
    change_message = models.CharField(max_length=255, blank=True, null=True)
    # Allow date/time styles to be defined if value is a date or time.
    DATE_STYLES = (('PKDateStyleNone', 'PKDateStyleNone'),
                   ('PKDateStyleShort', 'PKDateStyleShort'),
                   ('PKDateStyleMedium', 'PKDateStyleMedium'),
                   ('PKDateStyleLong', 'PKDateStyleLong'),
                   ('PKDateStyleFull', 'PKDateStyleFull'),)

    date_style = models.CharField(max_length=20, blank=True, null=True, choices=DATE_STYLES)
    time_style = models.CharField(max_length=20, blank=True, null=True, choices=DATE_STYLES)
    is_relative = models.NullBooleanField()

    # Allow number style keys if value is a number
    currency_code =  models.CharField(max_length=5, null=True, blank=True)

    NUMBER_STYLES = (('PKNumberStyleDecimal', 'Decimal'),
                     ('PKNumberStylePercent', 'Percentage'),
                     ('PKNumberStyleScientific', 'Scientific'),
                     ('PKNumberStyleSpellOut', 'Spelled Out'),)

    number_style = models.CharField(max_length=20, null=True, blank=True, choices=NUMBER_STYLES)

    def serialize(self):
        field = {
            'key': self.key,
            'label': self.label,
            'value': self.value
        }
        keys_and_attrs =  (
            ('textAlignment', 'text_alignment'),
            ('changeMessage', 'change_message'),
            ('dateStyle', 'date_style'),
            ('timeStyle', 'time_style'),
            ('isRelative', 'is_relative'),
            ('currencyCode', 'currency_code'),
            ('numberStyle', 'number_style'))

        for key, attr in keys_and_attrs:
            a = getattr(self, attr)
            if a is not None and a != '':
                field[key] = a

        return field

    def __unicode__(self):
        return u'Field: %s' % self.key


class Location(models.Model):
    longitude = models.FloatField()
    latitude = models.FloatField()
    altitude = models.FloatField(null=True)
    relevant_text = models.CharField(max_length=255, blank=True, null=True)

    def serialize(self):
        location = {'longitude': self.longitude,
                    'latitude': self.latitude}

        if self.altitude is not None:
            location['altitude'] = self.altitude
        if self.relevant_text is not None and self.relevant_text != '':
            location['relevantText'] = self.relevant_text

        return location
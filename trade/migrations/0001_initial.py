# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (("game", "0010_auto__add_field_trade_decline_reason"),)

    def forwards(self, orm):
        # Adding model 'Trade'
        db.create_table('trade_trade', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('initiator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='initiator_trades_set', to=orm['auth.User'])),
            ('responder', self.gf('django.db.models.fields.related.ForeignKey')(related_name='responder_trades_set', to=orm['auth.User'])),
            ('initiator_offer', self.gf('django.db.models.fields.related.OneToOneField')(related_name='trade_initiated', unique=True, to=orm['trade.Offer'])),
            ('responder_offer', self.gf('django.db.models.fields.related.OneToOneField')(related_name='trade_responded', unique=True, null=True, to=orm['trade.Offer'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='INITIATED', max_length=15)),
            ('decline_reason', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('finalizer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('closing_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('trade', ['Trade'])

        # Adding model 'Offer'
        db.create_table('trade_offer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('free_information', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('trade', ['Offer'])

        # Adding M2M table for field rules on 'Offer'
        db.create_table('trade_offer_rules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('offer', models.ForeignKey(orm['trade.offer'], null=False)),
            ('ruleinhand', models.ForeignKey(orm['game.ruleinhand'], null=False))
        ))
        db.create_unique('trade_offer_rules', ['offer_id', 'ruleinhand_id'])

        # Adding model 'TradedCommodities'
        db.create_table('trade_tradedcommodities', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('offer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['trade.Offer'])),
            ('commodity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.CommodityInHand'])),
            ('nb_traded_cards', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
        ))
        db.send_create_signal('trade', ['TradedCommodities'])

    def backwards(self, orm):
        # Deleting model 'Trade'
        db.delete_table('trade_trade')

        # Deleting model 'Offer'
        db.delete_table('trade_offer')

        # Removing M2M table for field rules on 'Offer'
        db.delete_table('trade_offer_rules')

        # Deleting model 'TradedCommodities'
        db.delete_table('trade_tradedcommodities')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'game.commodityinhand': {
            'Meta': {'object_name': 'CommodityInHand'},
            'commodity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.Commodity']"}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nb_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'game.game': {
            'Meta': {'object_name': 'Game'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mastering_games_set'", 'to': "orm['auth.User']"}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'playing_games_set'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['scoring.RuleCard']", 'symmetrical': 'False'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.Ruleset']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'game.ruleinhand': {
            'Meta': {'object_name': 'RuleInHand'},
            'abandon_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ownership_date': ('django.db.models.fields.DateTimeField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'rulecard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.RuleCard']"})
        },
        'scoring.commodity': {
            'Meta': {'object_name': 'Commodity'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'white'", 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.Ruleset']"}),
            'value': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'scoring.rulecard': {
            'Meta': {'object_name': 'RuleCard'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'glob': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_column': "'global'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mandatory': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ref_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.Ruleset']"}),
            'step': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'scoring.ruleset': {
            'Meta': {'object_name': 'Ruleset'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'trade.offer': {
            'Meta': {'object_name': 'Offer'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'commodities': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['game.CommodityInHand']", 'through': "orm['trade.TradedCommodities']", 'symmetrical': 'False'}),
            'free_information': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['game.RuleInHand']", 'symmetrical': 'False'})
        },
        'trade.trade': {
            'Meta': {'object_name': 'Trade'},
            'closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'decline_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'finalizer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'initiator_trades_set'", 'to': "orm['auth.User']"}),
            'initiator_offer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'trade_initiated'", 'unique': 'True', 'to': "orm['trade.Offer']"}),
            'responder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'responder_trades_set'", 'to': "orm['auth.User']"}),
            'responder_offer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'trade_responded'", 'unique': 'True', 'null': 'True', 'to': "orm['trade.Offer']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INITIATED'", 'max_length': '15'})
        },
        'trade.tradedcommodities': {
            'Meta': {'object_name': 'TradedCommodities'},
            'commodity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.CommodityInHand']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nb_traded_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'offer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['trade.Offer']"})
        }
    }

    complete_apps = ['trade']
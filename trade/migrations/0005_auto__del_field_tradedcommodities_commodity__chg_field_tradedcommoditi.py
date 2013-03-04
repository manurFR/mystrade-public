# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'TradedCommodities.commodity'
        db.delete_column('trade_tradedcommodities', 'commodity_id')

        # Renaming column for 'TradedCommodities.commodityinhand' to match new field type.
        db.rename_column('trade_tradedcommodities', 'commodityinhand', 'commodityinhand_id')
        # Changing field 'TradedCommodities.commodityinhand'
        db.alter_column('trade_tradedcommodities', 'commodityinhand_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.CommodityInHand']))
        # Adding index on 'TradedCommodities', fields ['commodityinhand']
        db.create_index('trade_tradedcommodities', ['commodityinhand_id'])


    def backwards(self, orm):
        # Removing index on 'TradedCommodities', fields ['commodityinhand']
        db.delete_index('trade_tradedcommodities', ['commodityinhand_id'])

        # Renaming column for 'TradedCommodities.commodityinhand' to match new field type.
        db.rename_column('trade_tradedcommodities', 'commodityinhand_id', 'commodityinhand')
        # Changing field 'TradedCommodities.commodityinhand'
        db.alter_column('trade_tradedcommodities', 'commodityinhand', self.gf('django.db.models.fields.IntegerField')(null=True))

#        # Adding field 'TradedCommodities.commodity'
#        db.add_column('trade_tradedcommodities', 'commodity',
#                      self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['game.CommodityInHand']),
#                      keep_default=False)

        # Adding field 'TradedCommodities.commodity'
        db.add_column('trade_tradedcommodities', 'commodity',
                      self.gf('django.db.models.fields.IntegerField')(null=True),
                      keep_default=False)


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
            'nb_submitted_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'game.game': {
            'Meta': {'object_name': 'Game'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mastering_games_set'", 'to': "orm['auth.User']"}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'playing_games_set'", 'symmetrical': 'False', 'through': "orm['game.GamePlayer']", 'to': "orm['auth.User']"}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['scoring.RuleCard']", 'symmetrical': 'False'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['scoring.Ruleset']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'game.gameplayer': {
            'Meta': {'object_name': 'GamePlayer'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
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
            'commodityinhand': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.CommodityInHand']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nb_traded_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'offer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['trade.Offer']"})
        }
    }

    complete_apps = ['trade']
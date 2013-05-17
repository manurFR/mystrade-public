# -*- coding: utf-8 -*-
from south.v2 import DataMigration
from django.db import connection, transaction
from mystrade import settings
from trade.models import Trade, Offer


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        orm['trade.TradedCommodities'].objects.all().delete()
        orm['trade.Offer'].objects.all().delete()
        orm['trade.Trade'].objects.all().delete()

        cursor = connection.cursor()

        for trade in Trade.objects.raw("SELECT * FROM game_trade"):
            old_initiator_offer = Offer.objects.raw("SELECT * FROM game_offer WHERE id = %s", [trade.initiator_offer_id])[0]
            initiator_offer = orm['trade.Offer'].objects.create(comment = old_initiator_offer.comment,
                                                                free_information = old_initiator_offer.free_information)
            # can't get this to work :(
            #cursor.execute("SELECT ruleinhand_id FROM game_offer_rules WHERE offer_id = %s", [old_initiator_offer.id])
            #for row in cursor.fetchall():
                #initiator_offer.rules.add(RuleInHand.objects.get(pk = row[0]))
            #for comm in TradedCommodities.objects.raw("SELECT * FROM game_tradedcommodities WHERE offer_id = %s", [old_initiator_offer.id]):
            #    orm['trade.TradedCommodities'].objects.create(offer = initiator_offer, commodity = comm.commodity, nb_traded_cards = comm.nb_traded_cards)
            cursor.execute("INSERT INTO trade_offer_rules (offer_id, ruleinhand_id) "
                           "SELECT %s, ruleinhand_id FROM game_offer_rules WHERE offer_id = %s",
                           [initiator_offer.id, old_initiator_offer.id])
            cursor.execute("INSERT INTO trade_tradedcommodities (offer_id, commodity_id, nb_traded_cards) "
                           "SELECT %s, commodity_id, nb_traded_cards FROM game_tradedcommodities WHERE offer_id = %s",
                           [initiator_offer.id, old_initiator_offer.id])

            if trade.responder_offer_id:
                old_responder_offer = Offer.objects.raw("SELECT * FROM game_offer WHERE id = %s", [trade.responder_offer_id])[0]
                responder_offer = orm['trade.Offer'].objects.create(comment = old_responder_offer.comment,
                                                                    free_information = old_responder_offer.free_information)

                #cursor.execute("SELECT ruleinhand_id FROM game_offer_rules WHERE offer_id = %s", [old_responder_offer.id])
                #for row in cursor.fetchall():
                #    responder_offer.rules.add(RuleInHand.objects.get(pk = row[0]))
                #responder_offer.save()
                #for comm in TradedCommodities.objects.raw("SELECT * FROM game_tradedcommodities WHERE offer_id = %s", [old_responder_offer.id]):
                #    orm['trade.TradedCommodities'].objects.create(offer = responder_offer, commodity = comm.commodity, nb_traded_cards = comm.nb_traded_cards)

                cursor.execute("INSERT INTO trade_offer_rules (offer_id, ruleinhand_id) "
                               "SELECT %s, ruleinhand_id FROM game_offer_rules WHERE offer_id = %s",
                               [responder_offer.id, old_responder_offer.id])
                cursor.execute("INSERT INTO trade_tradedcommodities (offer_id, commodity_id, nb_traded_cards) "
                               "SELECT %s, commodity_id, nb_traded_cards FROM game_tradedcommodities WHERE offer_id = %s",
                               [responder_offer.id, old_responder_offer.id])
            else:
                responder_offer = None

            orm['trade.Trade'].objects.create(game_id = trade.game_id, initiator_id = trade.initiator_id,
                                              responder_id = trade.responder_id, status = trade.status,
                                              decline_reason = trade.decline_reason,
                                              finalizer_id = trade.finalizer_id, creation_date = trade.creation_date,
                                              closing_date = trade.closing_date, initiator_offer = initiator_offer,
                                              responder_offer = responder_offer)

        transaction.commit_unless_managed()

    def backwards(self, orm):
        "Write your backwards methods here."

        cursor = connection.cursor()
        cursor.execute("DELETE FROM game_tradedcommodities")
        cursor.execute("DELETE FROM game_offer_rules")
        cursor.execute("DELETE FROM game_offer")
        cursor.execute("DELETE FROM game_trade")

        for trade in orm['trade.Trade'].objects.all():
            cursor.execute("INSERT INTO game_offer (comment, free_information) VALUES (%s, %s) RETURNING id",
                           [trade.initiator_offer.comment, trade.initiator_offer.free_information])
            initiator_offer_id = cursor.fetchone()[0]

            for rule in trade.initiator_offer.rules.all():
                cursor.execute("INSERT INTO game_offer_rules (offer_id, ruleinhand_id) VALUES (%s, %s)",
                               [initiator_offer_id, rule.id])
            for comm in trade.initiator_offer.tradedcommodities_set.all():
                cursor.execute("INSERT INTO game_tradedcommodities (offer_id, commodity_id, nb_traded_cards) VALUES (%s, %s, %s)",
                               [initiator_offer_id, comm.commodity.id, comm.nb_traded_cards])

            if trade.responder_offer:
                cursor.execute("INSERT INTO game_offer (comment, free_information) VALUES (%s, %s) RETURNING id",
                               [trade.responder_offer.comment, trade.responder_offer.free_information])
                responder_offer_id = cursor.fetchone()[0]

                for rule in trade.responder_offer.rules.all():
                    cursor.execute("INSERT INTO game_offer_rules (offer_id, ruleinhand_id) VALUES (%s, %s)",
                                   [responder_offer_id, rule.id])
                for comm in trade.responder_offer.tradedcommodities_set.all():
                    cursor.execute("INSERT INTO game_tradedcommodities (offer_id, commodity_id, nb_traded_cards) VALUES (%s, %s, %s)",
                                   [responder_offer_id, comm.commodity.id, comm.nb_traded_cards])
            else:
                responder_offer_id = None

            if trade.finalizer:
                finalizer_id = trade.finalizer.id
            else:
                finalizer_id = None

            cursor.execute("INSERT INTO game_trade (game_id, initiator_id, responder_id, status, creation_date, "
                           "closing_date, initiator_offer_id, responder_offer_id, finalizer_id, decline_reason) "
                           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           [trade.game.id, trade.initiator.id, trade.responder.id, trade.status, trade.creation_date,
                            trade.closing_date, initiator_offer_id, responder_offer_id, finalizer_id, trade.decline_reason])

        transaction.commit_unless_managed()

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
        u'profile.mystradeuser': {
            'Meta': {'object_name': 'MystradeUser'},
            'bio': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'send_notifications': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
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
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['" + settings.AUTH_USER_MODEL + "']"})
        },
        'game.game': {
            'Meta': {'object_name': 'Game'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mastering_games_set'", 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'playing_games_set'", 'symmetrical': 'False', 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
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
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
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
            'finalizer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm[" + settings.AUTH_USER_MODEL + "']", 'null': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'initiator_trades_set'", 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'initiator_offer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'trade_initiated'", 'unique': 'True', 'to': "orm['trade.Offer']"}),
            'responder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'responder_trades_set'", 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
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
    symmetrical = True
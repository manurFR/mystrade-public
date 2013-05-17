# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from mystrade import settings


class Migration(SchemaMigration):

    depends_on = (("profile", "0001_initial"),)

    def forwards(self, orm):

        # Changing field 'ScoreFromCommodity.player'
        db.alter_column(u'scoring_scorefromcommodity', 'player_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL]))

        # Changing field 'ScoreFromRule.player'
        db.alter_column(u'scoring_scorefromrule', 'player_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL]))

    def backwards(self, orm):

        # Changing field 'ScoreFromCommodity.player'
        db.alter_column(u'scoring_scorefromcommodity', 'player_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL]))

        # Changing field 'ScoreFromRule.player'
        db.alter_column(u'scoring_scorefromrule', 'player_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL]))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'game.game': {
            'Meta': {'object_name': 'Game'},
            'closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mastering_games_set'", 'to': u"orm['" + settings.AUTH_USER_MODEL + "']"}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'playing_games_set'", 'symmetrical': 'False', 'through': u"orm['game.GamePlayer']", 'to': u"orm['profile.MystradeUser']"}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['ruleset.RuleCard']", 'symmetrical': 'False'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.Ruleset']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'game.gameplayer': {
            'Meta': {'object_name': 'GamePlayer'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.MystradeUser']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        u'ruleset.commodity': {
            'Meta': {'object_name': 'Commodity'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'white'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.Ruleset']"}),
            'value': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'ruleset.rulecard': {
            'Meta': {'object_name': 'RuleCard'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'glob': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_column': "'global'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mandatory': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ref_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.Ruleset']"}),
            'step': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'ruleset.ruleset': {
            'Meta': {'object_name': 'Ruleset'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '510'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'scoring.scorefromcommodity': {
            'Meta': {'object_name': 'ScoreFromCommodity'},
            'actual_value': ('django.db.models.fields.IntegerField', [], {}),
            'commodity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.Commodity']"}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nb_scored_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'nb_submitted_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.MystradeUser']"}),
            'score': ('django.db.models.fields.IntegerField', [], {})
        },
        u'scoring.scorefromrule': {
            'Meta': {'object_name': 'ScoreFromRule'},
            'detail': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profile.MystradeUser']"}),
            'rulecard': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.RuleCard']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
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
        }
    }

    complete_apps = ['scoring']
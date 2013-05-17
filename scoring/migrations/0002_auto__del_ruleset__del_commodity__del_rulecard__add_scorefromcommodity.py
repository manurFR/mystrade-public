# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from mystrade import settings


class Migration(SchemaMigration):

    depends_on = (("ruleset", "0001_initial"),
                  ("game",    "0013_auto__chg_field_game_end_date"))

    def forwards(self, orm):
        # Deleting model 'Ruleset'
        db.delete_table('scoring_ruleset')

        # Deleting model 'Commodity'
        db.delete_table('scoring_commodity')

        # Deleting model 'RuleCard'
        db.delete_table('scoring_rulecard')

        # Adding model 'ScoreFromCommodity'
        db.create_table('scoring_scorefromcommodity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL])),
            ('commodity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ruleset.Commodity'])),
            ('nb_scored_cards', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('actual_value', self.gf('django.db.models.fields.IntegerField')()),
            ('score', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('scoring', ['ScoreFromCommodity'])

        # Adding model 'ScoreFromRule'
        db.create_table('scoring_scorefromrule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[settings.AUTH_USER_MODEL])),
            ('rulecard', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ruleset.RuleCard'])),
            ('detail', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('score', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('scoring', ['ScoreFromRule'])


    def backwards(self, orm):
        # Adding model 'Ruleset'
        db.create_table('scoring_ruleset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('scoring', ['Ruleset'])

        # Adding model 'Commodity'
        db.create_table('scoring_commodity', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('color', self.gf('django.db.models.fields.CharField')(default='white', max_length=20)),
            ('value', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scoring.Ruleset'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('scoring', ['Commodity'])

        # Adding model 'RuleCard'
        db.create_table('scoring_rulecard', (
            ('public_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('step', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('mandatory', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scoring.Ruleset'])),
            ('glob', self.gf('django.db.models.fields.BooleanField')(default=False, db_column='global')),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ref_name', self.gf('django.db.models.fields.CharField')(max_length=20, unique=True)),
        ))
        db.send_create_signal('scoring', ['RuleCard'])

        # Deleting model 'ScoreFromCommodity'
        db.delete_table('scoring_scorefromcommodity')

        # Deleting model 'ScoreFromRule'
        db.delete_table('scoring_scorefromrule')


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
        'game.game': {
            'Meta': {'object_name': 'Game'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'mastering_games_set'", 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'playing_games_set'", 'symmetrical': 'False', 'through': "orm['game.GamePlayer']", 'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'rules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ruleset.RuleCard']", 'symmetrical': 'False'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ruleset.Ruleset']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'game.gameplayer': {
            'Meta': {'object_name': 'GamePlayer'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'ruleset.commodity': {
            'Meta': {'object_name': 'Commodity'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'white'", 'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ruleset.Ruleset']"}),
            'value': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'ruleset.rulecard': {
            'Meta': {'object_name': 'RuleCard'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'glob': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_column': "'global'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mandatory': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'public_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'ref_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ruleset.Ruleset']"}),
            'step': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'ruleset.ruleset': {
            'Meta': {'object_name': 'Ruleset'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'scoring.scorefromcommodity': {
            'Meta': {'object_name': 'ScoreFromCommodity'},
            'actual_value': ('django.db.models.fields.IntegerField', [], {}),
            'commodity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ruleset.Commodity']"}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nb_scored_cards': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'score': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'scoring.scorefromrule': {
            'Meta': {'object_name': 'ScoreFromRule'},
            'detail': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['game.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['" + settings.AUTH_USER_MODEL + "']"}),
            'rulecard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ruleset.RuleCard']"}),
            'score': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['scoring']
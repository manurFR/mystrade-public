# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Ruleset'
        db.create_table('scoring_ruleset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('module', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('scoring', ['Ruleset'])

        # Adding model 'RuleCard'
        db.create_table('scoring_rulecard', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scoring.Ruleset'])),
            ('ref_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('public_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('mandatory', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('step', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('glob', self.gf('django.db.models.fields.BooleanField')(default=False, db_column='global')),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('scoring', ['RuleCard'])

        # Adding model 'Commodity'
        db.create_table('scoring_commodity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['scoring.Ruleset'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('color', self.gf('django.db.models.fields.CharField')(default='white', max_length=20)),
        ))
        db.send_create_signal('scoring', ['Commodity'])


    def backwards(self, orm):
        # Deleting model 'Ruleset'
        db.delete_table('scoring_ruleset')

        # Deleting model 'RuleCard'
        db.delete_table('scoring_rulecard')

        # Deleting model 'Commodity'
        db.delete_table('scoring_commodity')


    models = {
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
        }
    }

    complete_apps = ['scoring']
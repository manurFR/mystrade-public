# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Ruleset'
        db.create_table(u'ruleset_ruleset', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('module', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=510)),
        ))
        db.send_create_signal(u'ruleset', ['Ruleset'])

        # Adding model 'RuleCard'
        db.create_table(u'ruleset_rulecard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ruleset.Ruleset'])),
            ('ref_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('public_name', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('mandatory', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('step', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('glob', self.gf('django.db.models.fields.BooleanField')(default=False, db_column='global')),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'ruleset', ['RuleCard'])

        # Adding model 'Commodity'
        db.create_table(u'ruleset_commodity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ruleset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ruleset.Ruleset'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('color', self.gf('django.db.models.fields.CharField')(default='white', max_length=20)),
        ))
        db.send_create_signal(u'ruleset', ['Commodity'])


    def backwards(self, orm):
        # Deleting model 'Ruleset'
        db.delete_table(u'ruleset_ruleset')

        # Deleting model 'RuleCard'
        db.delete_table(u'ruleset_rulecard')

        # Deleting model 'Commodity'
        db.delete_table(u'ruleset_commodity')


    models = {
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
        }
    }

    complete_apps = ['ruleset']
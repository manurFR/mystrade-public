# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Ruleset.starting_rules'
        db.add_column(u'ruleset_ruleset', 'starting_rules',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=2),
                      keep_default=False)

        # Adding field 'Ruleset.starting_commodities'
        db.add_column(u'ruleset_ruleset', 'starting_commodities',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=10),
                      keep_default=False)

        # Adding field 'Ruleset.intro'
        db.add_column(u'ruleset_ruleset', 'intro',
                      self.gf('django.db.models.fields.CharField')(max_length=600, null=True),
                      keep_default=False)


        # Changing field 'Ruleset.description'
        db.alter_column(u'ruleset_ruleset', 'description', self.gf('django.db.models.fields.CharField')(max_length=600))

        # Adding field 'Commodity.category'
        db.add_column(u'ruleset_commodity', 'category',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Ruleset.starting_rules'
        db.delete_column(u'ruleset_ruleset', 'starting_rules')

        # Deleting field 'Ruleset.starting_commodities'
        db.delete_column(u'ruleset_ruleset', 'starting_commodities')

        # Deleting field 'Ruleset.intro'
        db.delete_column(u'ruleset_ruleset', 'intro')


        # Changing field 'Ruleset.description'
        db.alter_column(u'ruleset_ruleset', 'description', self.gf('django.db.models.fields.CharField')(max_length=510))

        # Deleting field 'Commodity.category'
        db.delete_column(u'ruleset_commodity', 'category')


    models = {
        u'ruleset.commodity': {
            'Meta': {'object_name': 'Commodity'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'color': ('django.db.models.fields.CharField', [], {'default': "'white'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ruleset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ruleset.Ruleset']"}),
            'symbol': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
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
            'description': ('django.db.models.fields.CharField', [], {'max_length': '600'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro': ('django.db.models.fields.CharField', [], {'max_length': '600', 'null': 'True'}),
            'module': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'starting_commodities': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '10'}),
            'starting_rules': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'})
        }
    }

    complete_apps = ['ruleset']
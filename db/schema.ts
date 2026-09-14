import { sqliteTable, text, integer, index } from 'drizzle-orm/sqlite-core';
export const uploads=sqliteTable('uploads',{
 id:text('id').primaryKey(),owner:text('owner').notNull(),name:text('name').notNull(),kind:text('kind').notNull(),size:integer('size').notNull(),mime:text('mime').notNull(),key:text('key').notNull(),multipart:text('multipart').notNull(),status:text('status').notNull(),created:integer('created').notNull(),
},t=>[index('uploads_owner_created').on(t.owner,t.created)]);
export const parts=sqliteTable('parts',{id:text('id').primaryKey(),upload:text('upload').notNull(),part:integer('part').notNull(),etag:text('etag').notNull(),size:integer('size').notNull()});
export const jobs=sqliteTable('jobs',{
 id:text('id').primaryKey(),owner:text('owner').notNull(),name:text('name').notNull(),media:text('media').notNull(),status:text('status').notNull(),stage:text('stage').notNull(),progress:integer('progress').notNull(),preset:text('preset').notNull(),transferred:integer('transferred').notNull().default(0),result:text('result'),report:text('report'),error:text('error'),created:integer('created').notNull(),updated:integer('updated').notNull(),lease:integer('lease').notNull().default(0),
},t=>[index('jobs_owner_created').on(t.owner,t.created)]);
export const settings=sqliteTable('settings',{owner:text('owner').primaryKey(),url:text('url').notNull(),token:text('token').notNull()});

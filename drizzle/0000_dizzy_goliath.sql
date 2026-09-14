CREATE TABLE `jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`name` text NOT NULL,
	`media` text NOT NULL,
	`status` text NOT NULL,
	`stage` text NOT NULL,
	`progress` integer NOT NULL,
	`preset` text NOT NULL,
	`transferred` integer DEFAULT 0 NOT NULL,
	`result` text,
	`report` text,
	`error` text,
	`created` integer NOT NULL,
	`updated` integer NOT NULL,
	`lease` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE INDEX `jobs_owner_created` ON `jobs` (`owner`,`created`);--> statement-breakpoint
CREATE TABLE `parts` (
	`id` text PRIMARY KEY NOT NULL,
	`upload` text NOT NULL,
	`part` integer NOT NULL,
	`etag` text NOT NULL,
	`size` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `settings` (
	`owner` text PRIMARY KEY NOT NULL,
	`url` text NOT NULL,
	`token` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `uploads` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`name` text NOT NULL,
	`kind` text NOT NULL,
	`size` integer NOT NULL,
	`mime` text NOT NULL,
	`key` text NOT NULL,
	`multipart` text NOT NULL,
	`status` text NOT NULL,
	`created` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `uploads_owner_created` ON `uploads` (`owner`,`created`);
/*
 ************************************************************
 * PostgreSQL driver Data Definition Language (DDL) Script. *
 ************************************************************
 */

CREATE SCHEMA IF NOT EXISTS red_config;
CREATE SCHEMA IF NOT EXISTS red_utils;

DO $$
BEGIN
  PERFORM 'red_config.identifier_data'::regtype;
EXCEPTION
  WHEN UNDEFINED_OBJECT THEN
    CREATE TYPE red_config.identifier_data AS (
      cog_name text,
      cog_id text,
      category text,
      pkeys text[],
      identifiers text[],
      pkey_len integer,
      is_custom boolean
    );
END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Create the config schema and/or table if they do not exist yet.
   */
  red_config.maybe_create_table(
    id_data red_config.identifier_data
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    schema_exists CONSTANT boolean := exists(
      SELECT 1
      FROM red_config.red_cogs t
      WHERE t.cog_name = id_data.cog_name AND t.cog_id = id_data.cog_id);
    table_exists CONSTANT boolean := schema_exists AND exists(
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = schemaname AND table_name = id_data.category);

  BEGIN
    IF NOT schema_exists THEN
      PERFORM red_config.create_schema(id_data.cog_name, id_data.cog_id);
    END IF;
    IF NOT table_exists THEN
      PERFORM red_config.create_table(id_data);
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Create the config schema for the given cog.
   */
  red_config.create_schema(new_cog_name text, new_cog_id text, OUT schemaname text)
    RETURNS text
    LANGUAGE 'plpgsql'
  AS $$
  BEGIN
    schemaname := concat_ws('.', new_cog_name, new_cog_id);

    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schemaname);

    INSERT INTO red_config.red_cogs AS t VALUES(new_cog_name, new_cog_id, schemaname)
    ON CONFLICT(cog_name, cog_id) DO UPDATE
    SET
      schemaname = excluded.schemaname;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Create the config table for the given category.
   */
  red_config.create_table(id_data red_config.identifier_data)
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    constraintname CONSTANT text := id_data.category||'_pkey';
    pkey_columns CONSTANT text := red_utils.gen_pkey_columns(1, id_data.pkey_len);
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    pkey_column_definitions CONSTANT text := red_utils.gen_pkey_column_definitions(
      1, id_data.pkey_len, pkey_type);

  BEGIN
    EXECUTE format(
      $query$
      CREATE TABLE IF NOT EXISTS %I.%I (
        %s,
        json_data jsonb DEFAULT '{}' NOT NULL,
        CONSTRAINT %I PRIMARY KEY (%s)
      )
      $query$,
      schemaname,
      id_data.category,
      pkey_column_definitions,
      constraintname,
      pkey_columns);
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Get config data.
   *
   * - When `pkeys` is a full primary key, all or part of a document
   * will be returned.
   * - When `pkeys` is not a full primary key, documents will be
   * aggregated together into a single JSONB object, with primary keys
   * as keys mapping to the documents.
   */
  red_config.get(
    id_data red_config.identifier_data,
    OUT result jsonb
  )
    LANGUAGE 'plpgsql'
    STABLE
    PARALLEL SAFE
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    num_pkeys CONSTANT integer := coalesce(array_length(id_data.pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer :=  id_data.pkey_len - num_pkeys;
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    whereclause CONSTANT text := red_utils.gen_whereclause(num_pkeys, pkey_type);

    table_exists CONSTANT boolean := exists(
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = schemaname AND table_name = id_data.category);

    missing_pkey_columns text;

  BEGIN
    IF NOT table_exists THEN
      -- If the table doesn't exist, just don't do anything to prevent SQL errors.
    ELSIF num_missing_pkeys <= 0 THEN
      -- No missing primary keys: we're getting all or part of a document.
      EXECUTE format(
        'SELECT json_data #> $2 FROM %I.%I WHERE %s',
        schemaname,
        id_data.category,
        whereclause)
      INTO result
      USING id_data.pkeys, id_data.identifiers;

    ELSIF num_missing_pkeys = 1 THEN
      -- 1 missing primary key: we can use the built-in jsonb_object_agg() aggregate function.
      EXECUTE format(
        'SELECT jsonb_object_agg(%I::text, json_data) FROM %I.%I WHERE %s',
        'primary_key_'||id_data.pkey_len,
        schemaname,
        id_data.category,
        whereclause)
      INTO result
      USING id_data.pkeys;
    ELSE
      -- Multiple missing primary keys: we must use our custom red_utils.jsonb_object_agg2()
      -- aggregate function.
      missing_pkey_columns := red_utils.gen_pkey_columns_casted(num_pkeys + 1, id_data.pkey_len);

      EXECUTE format(
        'SELECT red_utils.jsonb_object_agg2(json_data, %s) FROM %I.%I WHERE %s',
        missing_pkey_columns,
        schemaname,
        id_data.category,
        whereclause)
      INTO result
      USING id_data.pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Set config data.
   *
   * - When `pkeys` is a full primary key, all or part of a document
   * will be set.
   * - When `pkeys` is not a full set, multiple documents will be
   * replaced or removed - `new_value` must be a JSONB object mapping
   * primary keys to the new documents.
   *
   * Raises `error_in_assignment` error when trying to set a sub-key
   * of a non-document type.
   */
  red_config.set(
    id_data red_config.identifier_data,
    new_value jsonb
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    constraintname CONSTANT text := id_data.category||'_pkey';
    num_pkeys CONSTANT integer := coalesce(array_length(id_data.pkeys, 1), 0);
    num_missing_pkeys CONSTANT integer := id_data.pkey_len - num_pkeys;
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    pkey_placeholders CONSTANT text := red_utils.gen_pkey_placeholders(num_pkeys, pkey_type);

    new_document jsonb;
    pkey_column_definitions text;
    whereclause text;
    missing_pkey_columns text;

  BEGIN
    PERFORM red_config.maybe_create_table(id_data);

    IF num_missing_pkeys = 0 THEN
      -- Setting all or part of a document
      new_document := red_utils.jsonb_set2('{}', new_value, VARIADIC id_data.identifiers);

      EXECUTE format(
        $query$
        INSERT INTO %I.%I AS t VALUES (%s, $2)
        ON CONFLICT ON CONSTRAINT %I DO UPDATE
        SET
          json_data = red_utils.jsonb_set2(t.json_data, $3, VARIADIC $4)
        $query$,
        schemaname,
        id_data.category,
        pkey_placeholders,
        constraintname)
      USING id_data.pkeys, new_document, new_value, id_data.identifiers;

    ELSE
      -- Setting multiple documents
      whereclause := red_utils.gen_whereclause(num_pkeys, pkey_type);
      missing_pkey_columns := red_utils.gen_pkey_columns_casted(
        num_pkeys + 1, id_data.pkey_len, pkey_type);
      pkey_column_definitions := red_utils.gen_pkey_column_definitions(num_pkeys + 1, id_data.pkey_len);

      -- Delete all documents which we're setting first, since we don't know whether they'll be
      -- replaced by the subsequent INSERT.
      EXECUTE format('DELETE FROM %I.%I WHERE %s', schemaname, id_data.category, whereclause)
      USING id_data.pkeys;

      -- Insert all new documents
      EXECUTE format(
        $query$
        INSERT INTO %I.%I AS t
          SELECT %s, json_data
          FROM red_utils.generate_rows_from_object($2, $3) AS f(%s, json_data jsonb)
        ON CONFLICT ON CONSTRAINT %I DO UPDATE
        SET
          json_data = excluded.json_data
        $query$,
        schemaname,
        id_data.category,
        concat_ws(', ', pkey_placeholders, missing_pkey_columns),
        pkey_column_definitions,
        constraintname)
      USING id_data.pkeys, new_value, num_missing_pkeys;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Clear config data.
   *
   * - When `identifiers` is not empty, this will clear a key from a
   * document.
   * - When `identifiers` is empty and `pkeys` is not empty, it will
   * delete one or more documents.
   * - When `pkeys` is empty, it will drop the whole table.
   * - When `id_data.category` is NULL or an empty string, it will drop
   * the whole schema.
   *
   * Has no effect when the document or key does not exist.
   */
  red_config.clear(
    id_data red_config.identifier_data
  )
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    num_pkeys CONSTANT integer := coalesce(array_length(id_data.pkeys, 1), 0);
    num_identifiers CONSTANT integer := coalesce(array_length(id_data.identifiers, 1), 0);
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);

    schema_exists CONSTANT boolean := exists(
      SELECT 1
      FROM red_config.red_cogs t
      WHERE t.cog_name = id_data.cog_name AND t.cog_id = id_data.cog_id);
    table_exists CONSTANT boolean := schema_exists AND exists(
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = schemaname AND table_name = id_data.category);

    whereclause text;

  BEGIN
    -- If the schema or table doesn't exist, just don't do anything to prevent SQL errors.
    IF NOT schema_exists THEN
      -- pass
    ELSIF num_identifiers > 0 THEN
      IF NOT table_exists THEN
        RETURN;
      END IF;
      -- Popping a key from a document or nested document.
      whereclause := red_utils.gen_whereclause(num_pkeys, pkey_type);

      EXECUTE format(
        $query$
        UPDATE %I.%I AS t
        SET
          json_data = t.json_data #- $2
        WHERE %s
        $query$,
        schemaname,
        id_data.category,
        whereclause)
      USING id_data.pkeys, id_data.identifiers;

    ELSIF num_pkeys > 0 THEN
      IF NOT table_exists THEN
        RETURN;
      END IF;
      -- Deleting one or many documents
      whereclause := red_utils.gen_whereclause(num_pkeys, pkey_type);

      EXECUTE format('DELETE FROM %I.%I WHERE %s', schemaname, id_data.category, whereclause)
      USING id_data.pkeys;

    ELSIF id_data.category IS NOT NULL AND id_data.category != '' THEN
      IF NOT table_exists THEN
        RETURN;
      END IF;
      -- Deleting an entire category
      EXECUTE format('DROP TABLE %I.%I CASCADE', schemaname, id_data.category);

    ELSE
      -- Deleting an entire cog's data
      EXECUTE format('DROP SCHEMA %I CASCADE', schemaname);

      DELETE FROM red_config.red_cogs
      WHERE cog_name = id_data.cog_name AND cog_id = id_data.cog_id;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Increment a number within a document.
   *
   * If the value doesn't already exist, it is inserted as
   * `default_value + amount`.
   *
   * Raises 'wrong_object_type' error when trying to increment a
   * non-numeric value.
   */
  red_config.inc(
    id_data red_config.identifier_data,
    amount numeric,
    default_value numeric,
    OUT result numeric
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    num_identifiers CONSTANT integer := coalesce(array_length(id_data.identifiers, 1), 0);
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    whereclause CONSTANT text := red_utils.gen_whereclause(id_data.pkey_len, pkey_type);

    new_document jsonb;
    existing_document jsonb;
    existing_value jsonb;
    pkey_placeholders text;

  BEGIN
    IF num_identifiers = 0 THEN
      -- Without identifiers, there's no chance we're actually incrementing a number
      RAISE EXCEPTION 'Cannot increment document(s)'
      USING ERRCODE = 'wrong_object_type';
    END IF;

    PERFORM red_config.maybe_create_table(id_data);

    -- Look for the existing document
    EXECUTE format(
        'SELECT json_data FROM %I.%I WHERE %s',
        schemaname,
        id_data.category,
        whereclause)
    INTO existing_document USING id_data.pkeys;

    IF existing_document IS NULL THEN
      -- We need to insert a new document
      result := default_value + amount;
      new_document := red_utils.jsonb_set2('{}', result, VARIADIC id_data.identifiers);
      pkey_placeholders := red_utils.gen_pkey_placeholders(id_data.pkey_len, pkey_type);

      EXECUTE format(
        'INSERT INTO %I.%I VALUES(%s, $2)',
        schemaname,
        id_data.category,
        pkey_placeholders)
      USING id_data.pkeys, new_document;

    ELSE
      -- We need to update the existing document
      existing_value := existing_document #> id_data.identifiers;

      IF existing_value IS NULL THEN
        result := default_value + amount;

      ELSIF jsonb_typeof(existing_value) = 'number' THEN
        result := existing_value::text::numeric + amount;

      ELSE
        RAISE EXCEPTION 'Cannot increment non-numeric value %', existing_value
        USING ERRCODE = 'wrong_object_type';
      END IF;

      new_document := red_utils.jsonb_set2(
        existing_document, to_jsonb(result), id_data.identifiers);

      EXECUTE format(
        'UPDATE %I.%I SET json_data = $2 WHERE %s',
        schemaname,
        id_data.category,
        whereclause)
      USING id_data.pkeys, new_document;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Toggle a boolean within a document.
   *
   * If the value doesn't already exist, it is inserted as `NOT
   * default_value`.
   *
   * Raises 'wrong_object_type' error when trying to toggle a
   * non-boolean value.
   */
  red_config.toggle(
    id_data red_config.identifier_data,
    default_value boolean,
    OUT result boolean
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    num_identifiers CONSTANT integer := coalesce(array_length(id_data.identifiers, 1), 0);
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    whereclause CONSTANT text := red_utils.gen_whereclause(id_data.pkey_len, pkey_type);

    new_document jsonb;
    existing_document jsonb;
    existing_value jsonb;
    pkey_placeholders text;

  BEGIN
    IF num_identifiers = 0 THEN
      -- Without identifiers, there's no chance we're actually toggling a boolean
      RAISE EXCEPTION 'Cannot increment document(s)'
      USING ERRCODE = 'wrong_object_type';
    END IF;

    PERFORM red_config.maybe_create_table(id_data);

    -- Look for the existing document
    EXECUTE format(
      'SELECT json_data FROM %I.%I WHERE %s',
      schemaname,
      id_data.category,
      whereclause)
    INTO existing_document USING id_data.pkeys;

    IF existing_document IS NULL THEN
      -- We need to insert a new document
      result := NOT default_value;
      new_document := red_utils.jsonb_set2('{}', result, VARIADIC id_data.identifiers);
      pkey_placeholders := red_utils.gen_pkey_placeholders(id_data.pkey_len, pkey_type);

      EXECUTE format(
        'INSERT INTO %I.%I VALUES(%s, $2)',
        schemaname,
        id_data.category,
        pkey_placeholders)
      USING id_data.pkeys, new_document;

    ELSE
      -- We need to update the existing document
      existing_value := existing_document #> id_data.identifiers;

      IF existing_value IS NULL THEN
        result := NOT default_value;

      ELSIF jsonb_typeof(existing_value) = 'boolean' THEN
        result := NOT existing_value::text::boolean;

      ELSE
        RAISE EXCEPTION 'Cannot increment non-boolean value %', existing_value
        USING ERRCODE = 'wrong_object_type';
      END IF;

      new_document := red_utils.jsonb_set2(
        existing_document, to_jsonb(result), id_data.identifiers);

      EXECUTE format(
        'UPDATE %I.%I SET json_data = $2 WHERE %s',
        schemaname,
        id_data.category,
        whereclause)
      USING id_data.pkeys, new_document;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  red_config.extend(
    id_data red_config.identifier_data,
    new_value text,
    default_value text,
    max_length integer DEFAULT NULL,
    extend_left boolean DEFAULT FALSE,
    OUT result jsonb
  )
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    schemaname CONSTANT text := concat_ws('.', id_data.cog_name, id_data.cog_id);
    num_identifiers CONSTANT integer := coalesce(array_length(id_data.identifiers, 1), 0);
    pkey_type CONSTANT text := red_utils.get_pkey_type(id_data.is_custom);
    whereclause CONSTANT text := red_utils.gen_whereclause(id_data.pkey_len, pkey_type);
    pop_idx CONSTANT integer := CASE extend_left WHEN TRUE THEN -1 ELSE 0 END;

    new_document jsonb;
    existing_document jsonb;
    existing_value jsonb;
    pkey_placeholders text;
    idx integer;
  BEGIN
    IF num_identifiers = 0 THEN
      -- Without identifiers, there's no chance we're actually appending to an array
      RAISE EXCEPTION 'Cannot append to document(s)'
      USING ERRCODE = 'wrong_object_type';
    END IF;

    PERFORM red_config.maybe_create_table(id_data);

    -- Look for the existing document
    EXECUTE format(
      'SELECT json_data FROM %I.%I WHERE %s',
      schemaname,
      id_data.category,
      whereclause)
    INTO existing_document USING id_data.pkeys;

    IF existing_document IS NULL THEN
      result := default_value || new_value;
      new_document := red_utils.jsonb_set2('{}'::jsonb, result, id_data.identifiers);
      pkey_placeholders := red_utils.gen_pkey_placeholders(id_data.pkey_len, pkey_type);

      EXECUTE format(
        'INSERT INTO %I.%I VALUES(%s, $2)',
        schemaname,
        id_data.category,
        pkey_placeholders)
      USING id_data.pkeys, new_document;

    ELSE
      existing_value := existing_document #> id_data.identifiers;

      IF existing_value IS NULL THEN
        existing_value := default_value;

      ELSIF jsonb_typeof(existing_value) != 'array' THEN
        RAISE EXCEPTION 'Cannot append to non-array value %', existing_value
        USING ERRCODE = 'wrong_object_type';
      END IF;

      CASE extend_left
        WHEN TRUE THEN
          result := new_value || existing_value;
        ELSE
          result := existing_value || new_value;
        END CASE;

      IF max_length IS NOT NULL THEN
        FOR idx IN SELECT generate_series(1, jsonb_array_length(result) - max_length) LOOP
          result := result - pop_idx;
        END LOOP;
      END IF;

      new_document := red_utils.jsonb_set2(existing_document, result, id_data.identifiers);

      EXECUTE format(
        'UPDATE %I.%I SET json_data = $2 WHERE %s',
        schemaname,
        id_data.category,
        whereclause)
      USING id_data.pkeys, new_document;
    END IF;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Delete all schemas listed in the red_config.red_cogs table.
   */
  red_config.delete_all_schemas()
    RETURNS void
    LANGUAGE 'plpgsql'
  AS $$
  DECLARE
    cog_entry record;
  BEGIN
    FOR cog_entry IN SELECT * FROM red_config.red_cogs t LOOP
      EXECUTE format('DROP SCHEMA %I CASCADE', cog_entry.schemaname);
    END LOOP;
    -- Clear out red_config.red_cogs table
    DELETE FROM red_config.red_cogs WHERE TRUE;
  END;
$$;



CREATE OR REPLACE FUNCTION
  /*
   * Like `jsonb_set` but will insert new objects where one is missing
   * along the path.
   *
   * Raises `error_in_assignment` error when trying to set a sub-key
   * of a non-document type.
   */
  red_utils.jsonb_set2(target jsonb, new_value jsonb, VARIADIC identifiers text[])
    RETURNS jsonb
    LANGUAGE 'plpgsql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
  DECLARE
    num_identifiers CONSTANT integer := coalesce(array_length(identifiers, 1), 0);

    cur_value_type text;
    idx integer;

  BEGIN
    IF num_identifiers = 0 THEN
      RETURN new_value;
    END IF;

    FOR idx IN SELECT generate_series(1, num_identifiers - 1) LOOP
      cur_value_type := jsonb_typeof(target #> identifiers[:idx]);
      IF cur_value_type IS NULL THEN
        -- Parent key didn't exist in JSON before - insert new object
        target := jsonb_set(target, identifiers[:idx], '{}'::jsonb);

      ELSIF cur_value_type != 'object' THEN
        -- We can't set the sub-field of a null, int, float, array etc.
        RAISE EXCEPTION 'Cannot set sub-field of "%s"', cur_value_type
        USING ERRCODE = 'error_in_assignment';
      END IF;
    END LOOP;

    RETURN jsonb_set(target, identifiers, new_value);
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Return a set of rows to insert into a table, from a single JSONB
   * object containing multiple documents.
   */
  red_utils.generate_rows_from_object(object jsonb, num_missing_pkeys integer)
    RETURNS setof record
    LANGUAGE 'plpgsql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
  DECLARE
    pair record;
    column_definitions text;
  BEGIN
    IF num_missing_pkeys = 1 THEN
      -- Base case: Simply return (key, value) pairs
      RETURN QUERY
        SELECT key AS key_1, value AS json_data
        FROM jsonb_each(object);
    ELSE
      -- We need to return (key, key, ..., value) pairs: recurse into inner JSONB objects
      column_definitions := red_utils.gen_pkey_column_definitions(2, num_missing_pkeys);

      FOR pair IN SELECT * FROM jsonb_each(object) LOOP
        RETURN QUERY
          EXECUTE format(
            $query$
            SELECT $1 AS key_1, *
            FROM red_utils.generate_rows_from_object($2, $3)
              AS f(%s, json_data jsonb)
            $query$,
            column_definitions)
          USING pair.key, pair.value, num_missing_pkeys - 1;
      END LOOP;
    END IF;
    RETURN;
  END;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Get a comma-separated list of primary key placeholders.
   *
   * The placeholder will always be $1. Particularly useful for
   * inserting values into a table from an array of primary keys.
   */
  red_utils.gen_pkey_placeholders(num_pkeys integer, pkey_type text DEFAULT 'text')
    RETURNS text
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('$1[%s]::%s', idx, pkey_type) AS item
      FROM generate_series(1, num_pkeys) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a whereclause for the given number of primary keys.
   *
   * When there are no primary keys, this will simply return the the
   * string 'TRUE'. When there are multiple, it will return multiple
   * equality comparisons concatenated with 'AND'.
   */
  red_utils.gen_whereclause(num_pkeys integer, pkey_type text)
    RETURNS text
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT coalesce(string_agg(t.item, ' AND '), 'TRUE')
    FROM (
      SELECT format('%I = $1[%s]::%s', 'primary_key_'||idx, idx, pkey_type) AS item
      FROM generate_series(1, num_pkeys) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a comma-separated list of primary key column names.
   */
  red_utils.gen_pkey_columns(start integer, stop integer)
    RETURNS text
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT quote_ident('primary_key_'||idx) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;

CREATE OR REPLACE FUNCTION
  /*
   * Generate a comma-separated list of primary key column names casted
   * to the given type.
   */
  red_utils.gen_pkey_columns_casted(start integer, stop integer, pkey_type text DEFAULT 'text')
    RETURNS text
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('%I::%s', 'primary_key_'||idx, pkey_type) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;


CREATE OR REPLACE FUNCTION
  /*
   * Generate a primary key column definition list.
   */
  red_utils.gen_pkey_column_definitions(
    start integer, stop integer, column_type text DEFAULT 'text'
  )
    RETURNS text
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT string_agg(t.item, ', ')
    FROM (
      SELECT format('%I %s', 'primary_key_'||idx, column_type) AS item
      FROM generate_series(start, stop) idx) t
    ;
$$;


CREATE OR REPLACE FUNCTION
  red_utils.get_pkey_type(is_custom boolean)
    RETURNS TEXT
    LANGUAGE 'sql'
    IMMUTABLE
    PARALLEL SAFE
  AS $$
    SELECT ('{bigint,text}'::text[])[is_custom::integer + 1];
$$;


DROP AGGREGATE IF EXISTS red_utils.jsonb_object_agg2(jsonb, VARIADIC text[]);
CREATE AGGREGATE
  /*
   * Like `jsonb_object_agg` but aggregates more than two columns into a
   * single JSONB object.
   *
   * If possible, use `jsonb_object_agg` instead for performance
   * reasons.
   */
  red_utils.jsonb_object_agg2(json_data jsonb, VARIADIC primary_keys text[]) (
    SFUNC = red_utils.jsonb_set2,
    STYPE = jsonb,
    INITCOND = '{}',
    PARALLEL = SAFE
  )
;


CREATE TABLE IF NOT EXISTS
  /*
   * Table to keep track of other cogs' schemas.
   */
  red_config.red_cogs(
    cog_name text,
    cog_id text,
    schemaname text NOT NULL,
    PRIMARY KEY (cog_name, cog_id)
)
;

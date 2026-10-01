CREATE DATABASE sample;

GRANT ALL PRIVILEGES ON DATABASE sample TO airflow;

\connect sample

CREATE TABLE
    crm (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        country VARCHAR(50),
        prosthesis_id VARCHAR(50),
        created_at TIMESTAMP DEFAULT now (),
        updated_at TIMESTAMP DEFAULT now ()
    );

CREATE TABLE
    telemetry (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        prosthesis_id VARCHAR(50),
        ts TIMESTAMP NOT NULL,
        metric_type VARCHAR(50),
        metric_value FLOAT
    );

INSERT INTO
    crm (email, name, country, prosthesis_id)
VALUES
    (
        'prothetic1@example.com',
        'prothetic1',
        'RU',
        'P001'
    ),
    (
        'prothetic2@example.com',
        'prothetic2',
        'DE',
        'P002'
    ),
    (
        'prothetic3@example.com',
        'prothetic3',
        'CN',
        'P003'
    );

INSERT INTO
    telemetry (
        user_id,
        prosthesis_id,
        ts,
        metric_type,
        metric_value
    )
VALUES
    (1, 'P001', '2025-09-20 10:15:00', 'type_1', 10.0),
    (1, 'P001', '2025-09-20 11:45:00', 'type_1', 15.0),
    (1, 'P001', '2025-09-20 15:00:00', 'type_1', 12.0),
    (1, 'P001', '2025-09-21 09:20:00', 'type_1', 18.0),
    (1, 'P001', '2025-09-21 13:05:00', 'type_2', 20.0),
    (2, 'P002', '2025-09-20 08:10:00', 'type_1', 8.0),
    (2, 'P002', '2025-09-20 19:30:00', 'type_1', 11.0),
    (2, 'P002', '2025-09-21 10:00:00', 'type_1', 9.0),
    (3, 'P003', '2025-09-20 14:10:00', 'type_2', 25.0),
    (3, 'P003', '2025-09-20 18:40:00', 'type_2', 27.0);
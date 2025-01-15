CREATE TABLE IF NOT EXISTS toto_results (
    id SERIAL PRIMARY KEY,
    draw_number INTEGER UNIQUE NOT NULL,
    winning_numbers INTEGER[] NOT NULL,
    additional_number INTEGER NOT NULL,
    draw_date TIMESTAMP NOT NULL,
    jackpot DECIMAL NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS winning_shares (
    id SERIAL PRIMARY KEY,
    draw_number INTEGER REFERENCES toto_results (draw_number),
    group_number INTEGER NOT NULL,
    share_amount DECIMAL NULL,
    winner_count INTEGER NULL,
    UNIQUE (draw_number, group_number)
);

CREATE TABLE IF NOT EXISTS snowball_info (
    id SERIAL PRIMARY KEY,
    draw_number INTEGER REFERENCES toto_results (draw_number),
    group_number INTEGER NOT NULL,
    amount DECIMAL NOT NULL,
    UNIQUE (draw_number, group_number)
);

CREATE TABLE IF NOT EXISTS winning_locations (
    id SERIAL PRIMARY KEY,
    draw_number INTEGER REFERENCES toto_results (draw_number),
    group_number INTEGER NOT NULL,
    outlet_name TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    UNIQUE (draw_number, group_number, outlet_name)
);

CREATE INDEX idx_draw_number ON toto_results (draw_number);

CREATE INDEX idx_draw_date ON toto_results (draw_date);
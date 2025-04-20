CREATE TABLE IF NOT EXISTS toto_page (
    id SERIAL PRIMARY KEY,
    draw_number INTEGER UNIQUE NOT NULL,
    html_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_toto_page_draw_number ON toto_page (draw_number);

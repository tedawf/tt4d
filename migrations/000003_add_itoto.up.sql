CREATE TABLE IF NOT EXISTS winning_tickets (
  id SERIAL PRIMARY KEY,
  draw_number INTEGER NOT NULL REFERENCES toto_results (draw_number) ON DELETE CASCADE,
  group_number INTEGER NOT NULL,
  outlet_name TEXT NOT NULL,
  outlet_address TEXT,
  entry_type TEXT NOT NULL,
  is_itoto BOOLEAN DEFAULT FALSE,
  ticket_order INTEGER NOT NULL,
  UNIQUE (draw_number, group_number, ticket_order)
);

CREATE TABLE IF NOT EXISTS itoto_locations (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES winning_tickets(id) ON DELETE CASCADE,
    outlet_name TEXT NOT NULL,
    outlet_address TEXT NOT NULL,
    share_count INTEGER NOT NULL CHECK (share_count > 0),
    location_order INTEGER NOT NULL,
    UNIQUE (ticket_id, outlet_name, outlet_address)
);
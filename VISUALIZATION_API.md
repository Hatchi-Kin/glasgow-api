# Music Visualization API

This API provides endpoints for managing and querying 3D visualization data of music tracks based on embeddings (512D → PCA 50D → t-SNE 3D).

## Database Schema

### `track_visualization` Table

```sql
CREATE TABLE track_visualization (
    id INTEGER PRIMARY KEY REFERENCES megaset(id) ON DELETE CASCADE,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    cluster INTEGER NOT NULL,
    cluster_color VARCHAR(7) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

The `id` field references the `megaset` table, allowing joins to get track metadata (title, artist, album, genre, year).

## Setup

### 1. Create the Table

```bash
POST /visualization/create_table
```

### 2. Load Data from MinIO

```bash
POST /visualization/load_data?bucket_name=megaset&object_name=music_visualization_data.json
```

This expects a JSON file with the following structure:

```json
{
  "points": [
    {
      "id": 725,
      "x": 1.234,
      "y": -0.567,
      "z": 0.890,
      "cluster": 5,
      "cluster_color": "#FF6B6B",
      "title": "No Biggie",
      "artist": "Logic",
      "album": "Young Sinatra: Undeniable",
      "genre": "Hip-Hop",
      "year": 2010
    }
  ],
  "clusters": {
    "5": {
      "id": 5,
      "color": "#FF6B6B",
      "count": 342,
      "center": [0.5, -0.2, 0.8]
    }
  }
}
```

## API Endpoints

### Get All Points

```bash
GET /visualization/points?limit=10000&offset=0
```

Returns visualization points with track metadata joined from the `megaset` table.

**Response:**
```json
{
  "points": [...],
  "total": 15234,
  "limit": 10000,
  "offset": 0
}
```

### Get Statistics

```bash
GET /visualization/stats
```

Returns overall statistics including:
- Total tracks
- Total clusters
- Genre distribution
- Top 10 genres
- Largest cluster info

### Search Tracks

```bash
GET /visualization/search?q=logic&limit=50
```

Search by title, artist, album, or genre (case-insensitive).

### Get Cluster Details

```bash
GET /visualization/cluster/5
```

Returns all tracks in a specific cluster with cluster metadata.

### Get Track Neighbors

```bash
GET /visualization/track/725/neighbors?limit=20
```

Returns the nearest neighbors of a track in 3D space using Euclidean distance.

## Usage Flow

1. **Initial Setup:**
   ```bash
   POST /visualization/create_table
   POST /visualization/load_data
   ```

2. **Query Data:**
   ```bash
   GET /visualization/points?limit=10000
   GET /visualization/stats
   ```

3. **Interactive Queries:**
   ```bash
   GET /visualization/search?q=hip-hop
   GET /visualization/cluster/5
   GET /visualization/track/725/neighbors?limit=20
   ```

## Notes

- The `id` in the JSON must match existing track IDs in the `megaset` table
- The table uses a foreign key constraint, so tracks must exist in `megaset` before loading visualization data
- Cluster ID `-1` typically represents noise points (outliers not assigned to any cluster)
- The API automatically joins with `megaset` to provide rich metadata (title, artist, album, genre, year)

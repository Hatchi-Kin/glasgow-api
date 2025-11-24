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


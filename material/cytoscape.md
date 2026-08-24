# Visualising Networks — Cytoscape

Session: **Day 3, 11:00–11:30** ·
Notebook: [`notebooks/05_Visualising_Networks/04_nxpandas.ipynb`](../notebooks/05_Visualising_Networks/04_nxpandas.ipynb)

[Cytoscape](https://cytoscape.org/) is the standard desktop tool for biological networks:
interactive layout, styling driven by node and edge attributes, and a large app ecosystem.
NetworkX is better for *computing* on a graph; Cytoscape is better for *looking* at one and
for producing a figure someone else can read.

## Before the session

**Install Cytoscape** from <https://cytoscape.org/download.html> (free, Windows/macOS/Linux,
needs Java — the installer bundles it). Open it once to check it starts.

Optional apps worth having (`Apps → App Store`):

| App | What it adds |
|---|---|
| [**stringApp**](https://apps.cytoscape.org/apps/stringapp) | pulls STRING protein–protein interactions and functional enrichment straight into Cytoscape |
| [**yFiles Layout Algorithms**](https://apps.cytoscape.org/apps/yfileslayoutalgorithms) | hierarchical and organic layouts, good for two-layer networks |
| [**MetScape**](https://apps.cytoscape.org/apps/metscape) | metabolite–gene networks from KEGG |
| [**clusterMaker2**](https://apps.cytoscape.org/apps/clustermaker2) | community detection inside Cytoscape |

## What we import

The notebooks write two kinds of export. Both describe the same graph; use whichever fits.

| File | Written by | Load with |
|---|---|---|
| `*.graphml` | `nx.write_graphml` | `File → Import → Network from File…` — topology *and* all attributes in one go |
| `*_edges.csv` + `*_nodes.csv` | pandas | two imports, below — the route that always works, and the one you need when the attributes come from elsewhere |

Day 3 morning (`04_nxpandas`) exports a **protein co-abundance network**; Day 3 afternoon
(`multiomics/notebooks/02_multiomics_networks`) exports a **cross-omics protein–metabolite
network**. The instructions are identical.

## Importing the tables

**1. The network**

`File → Import → Network from File…` → the edge CSV. In the dialog:

- click the `source` column header and set it to **Source Node**
- click `target` and set it to **Target Node**
- leave `rho`, `abs_rho`, `padj`, `sign` as **Edge Attribute**

**2. The node attributes**

`File → Import → Table from File…` → the node CSV.

- *Where to Import Table Data*: **To selected networks only**
- *Key Column for Network*: `shared name`
- *Key* (in the file): the first column (`node` or `protein_group`)

If nothing appears afterwards, the keys did not match. Check that the node identifiers in
both files are written the same way — this is the only step that usually goes wrong.

## Styling: the part that matters

An unstyled network is a hairball. Styling is what turns it into a figure. Open the **Style**
panel (left), and set mappings by clicking a property's *Mapping* row.

For the **cross-omics** network:

| Visual property | Column | Mapping type | Notes |
|---|---|---|---|
| Node Label | `label` | Passthrough | gene symbol or metabolite name |
| Node Shape | `layer` | Discrete | e.g. rectangle = protein, ellipse = metabolite |
| Node Fill Colour | `community` | Discrete | one colour per module |
| Node Size | `degree` | Continuous | 20 → 60 |
| Edge Stroke Colour | `rho` | Continuous | diverging blue → white → red, centred on 0 |
| Edge Width | `abs_rho` | Continuous | 1 → 6 |

For the **protein co-abundance** network:

| Visual property | Column | Mapping type |
|---|---|---|
| Node Label | `gene` | Passthrough |
| Node Fill Colour | `log2fc_CRKP_vs_KP` | Continuous, diverging, centred on 0 |
| Node Border Width | `is_dep_CRKP_vs_KP` | Discrete — thick border for published differential proteins |
| Node Size | `degree` | Continuous |
| Edge Stroke Colour | correlation sign | Discrete |

> 💡 For a continuous colour mapping, double-click the mapping to open the gradient editor and
> **set the midpoint to 0** explicitly. A diverging palette whose centre drifts to the data
> mean is actively misleading.

## Layout

`Layout → Prefuse Force Directed` is the sensible default. Two others are worth knowing:

- `Layout → yFiles Hierarchic` — shows the two omics layers as two tiers
- `Layout → Attribute Circle Layout` using `community` — groups modules visibly

Then tidy by hand. Nobody publishes a layout straight from the algorithm.

## Getting a figure out

`File → Export → Network to Image…` → **PDF** or **SVG**, not PNG: vector output stays sharp
in a poster or a paper, and the text remains editable.

Remember to include a legend. Cytoscape does not draw one; add it in your figure editor, and
state in the caption **what an edge means** — for a correlation network, that two molecules
rise and fall together across patients, which is a hypothesis about co-regulation, shared
tissue origin or a shared upstream driver, and *not* a physical interaction.

## Driving Cytoscape from Python

With Cytoscape running on the same machine, [py4cytoscape](https://py4cytoscape.readthedocs.io/)
turns all of the above into code:

```python
import py4cytoscape as p4c

p4c.cytoscape_ping()                     # check the connection
p4c.create_network_from_networkx(graph, title="cross-omics", collection="course")
p4c.set_node_label_mapping("label")
p4c.set_node_size_mapping("degree", table_column_values=[1, 20], sizes=[20, 60])
p4c.set_edge_color_mapping("rho", table_column_values=[-1, 0, 1],
                           colors=["#4C72B0", "#FFFFFF", "#C44E52"])
p4c.layout_network("force-directed")
p4c.export_image("network.pdf", type="PDF")
```

Convenient, and reproducible — but it needs a live Cytoscape on `localhost`, so it does not
work from Colab. The file route always works.

## Exercise for the session

1. Import the cross-omics network and style it as above.
2. Find the highest-degree protein. Use `stringApp` to ask what is known about it.
3. Select one community, `File → New Network → From Selected Nodes`, lay it out separately,
   and export it as a PDF.
4. Write the figure caption — including one sentence on what the edges do **not** mean.

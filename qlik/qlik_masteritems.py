from qlik_sdk import AuthType, Config, Qlik
import json
import os
import sys
import requests
from pathlib import Path

class Qlik_Masteritems:

    @staticmethod
    def _load_config() -> dict:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qlik_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {}

    def __init__(self, app_id: str, save_dir: Path = None):
        config = self._load_config()
        tenant_url = config.get("_QLIK_TENANT_URL_")
        self.api_key = config.get("_QLIK_API_KEY_")

        if not tenant_url:
            print("ERROR: _QLIK_TENANT_URL_ is not set. Run: qlik set_tenant <url>")
            sys.exit(1)
        if not self.api_key:
            print("ERROR: _QLIK_API_KEY_ is not set. Run: qlik set_tenant_api_key <key>")
            sys.exit(1)

        self.tenant_host = tenant_url.rstrip("/")
        self.app_id = app_id
        self.save_dir = save_dir or Path(__file__).parent
        self.app = None
        self.connect()

    def connect(self) -> None:
        config = Config(
            host=self.tenant_host,
            auth_type=AuthType.APIKey,
            api_key=self.api_key,
        )
        qlik = Qlik(config)
        self.app = qlik.apps.get(self.app_id)
        self.app.open()
 

    def close(self) -> None:
        if self.app:
            self.app.close()

    def master_measure_exists(self, title: str, id: str = None) -> list[dict]:
        """Returns a list of matching master measures as dicts. Empty list if none found, multiple entries if duplicates exist."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qMeasure": "/qMeasure",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = measures.get_layout()
        return [
            {
                "id":          m.qInfo.qId,
                "title":       m.qMeta.title,
                "description": m.qMeta.description,
                "definition":  m.qData.qMeasure.get("qDef", ""),
                "label":       m.qData.qMeasure.get("qLabelExpression", ""),
                "fmt":         m.qData.qMeasure.get("qNumFormat", {}).get("qFmt", ""),
                "tags":        getattr(m.qData, "tags", []),
            }
            for m in layout.qMeasureList.qItems
            if m.qMeta.title == title
            and (id is None or m.qInfo.qId == id)
        ]

    def delete_master_measure(self, title: str) -> bool:
        """Deletes a master measure by name. Returns True if deleted, False if not found."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                }
            }
        })

        layout = measures.get_layout()
        for m in layout.qMeasureList.qItems:
            if m.qMeta.title == title:
                print(f"Deleting master measure {title}")
                self.app.destroy_measure(m.qInfo.qId)
                self.app.do_save()
                return True
        return False

    def update_master_measure_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], fmt: str = None, id: str = None) -> bool:
        """Updates an existing master measure in-place. Returns True if found and updated, False otherwise.
        If id is provided, matches by ID; otherwise matches by name."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {"title": "/qMetaDef/title"}
            }
        })

        layout = measures.get_layout()
        for m in layout.qMeasureList.qItems:
            if id is not None and m.qInfo.qId == id or id is None and m.qMeta.title == title:
                measure_obj = self.app.get_measure(m.qInfo.qId)
                props = measure_obj.get_properties()
                num_format = {"qType": "F", "qFmt": fmt, "qDec": ".", "qThou": " ", "qUseThou": 1} if fmt else {"qType": "U"}
                props.qMeasure.qDef = definition
                props.qMeasure.qLabel = title
                props.qMeasure.qLabelExpression = label or title
                props.qMeasure.qNumFormat = num_format
                props.qMetaDef.title = title
                props.qMetaDef.description = description
                props.qMetaDef.tags = tags
                measure_obj.set_properties(props)
                self.app.do_save()
                return True
        return False

    def create_master_measure_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], fmt: str = None, id: str = None) -> None:
        """Creates a master measure expression and saves it to the app."""

        num_format = {"qType": "F", "qFmt": fmt, "qDec": ".", "qThou": " ", "qUseThou": 1} if fmt else {"qType": "U"}

        self.app.create_measure({
            "qInfo": {
                "qType": "measure"
            },
            "qMeasure": {
                "qDef": definition,
                "qLabel": title,
                "qLabelExpression": label,
                "qNumFormat": num_format,
            },
            "qMetaDef": {
                "title": title,
                "description": description,
                "tags": tags,
            }
        })

        self.app.do_save()


    def create_measures(self) -> None:
        """Loads measures from measures.json and creates or updates them. Skips and logs duplicates."""

        with open(self.save_dir / "measures.json", "r", encoding="utf-8") as f:
            measures = json.load(f)

        duplicates_path = self.save_dir / "measures_duplicates.json"

        for measure in measures:
            args = dict(
                title=measure["title"],
                definition=measure["definition"],
                description=measure.get("description", ""),
                label=measure.get("label", ""),
                tags=measure.get("tags", []),
                fmt=measure.get("fmt"),
                id=measure.get("id", None),
            )

            matches = self.master_measure_exists(measure["title"], measure["id"])

            if len(matches) == 0:
                print(f"Creating: '{measure['title']}' ✅")
                self.create_master_measure_expr(**args)
            elif len(matches) == 1:
                print(f"Updating: '{measure['title']}' ✅")
                self.update_master_measure_expr(**args)
            else:
                print(f"⚠️ WARNING: {len(matches)} duplicates found for '{measure['title']}' — skipping. Written to measures_duplicates.json")
                raw = duplicates_path.read_text(encoding="utf-8").strip() if duplicates_path.exists() else ""
                existing = json.loads(raw) if raw else []
                existing_ids = {m["id"] for entry in existing for m in entry.get("qlik_matches", [])}
                new_matches = [m for m in matches if m["id"] not in existing_ids]
                if new_matches:
                    existing.append({
                        "source": measure,
                        "qlik_matches": new_matches,
                    })
                    duplicates_path.write_text(json.dumps(existing, indent=4), encoding="utf-8")

    def master_dimension_exists(self, title: str, id: str = None) -> list[dict]:
        """Returns a list of matching master dimensions as dicts. Empty list if none found, multiple entries if duplicates exist."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qDim": "/qDim",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = dimensions.get_layout()
        return [
            {
                "id":          m.qInfo.qId,
                "title":       m.qMeta.title,
                "description": m.qMeta.description,
                "definition":        (m.qData.qDim.get("qFieldDefs") or [""])[0],
                "label":             (m.qData.qDim.get("qFieldLabels") or [""])[0],
                "label_expression":  m.qData.qDim.get("qLabelExpression", ""),
                "tags":              getattr(m.qData, "tags", []),
            }
            for m in layout.qDimensionList.qItems
            if m.qMeta.title == title
            and (id is None or m.qInfo.qId == id)
        ]

    def delete_master_dimension(self, title: str) -> bool:
        """Deletes a master dimension by name. Returns True if deleted, False if not found."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                }
            }
        })

        layout = dimensions.get_layout()
        for m in layout.qDimensionList.qItems:
            if m.qMeta.title == title:
                print(f"Deleting master dimension {title}")
                self.app.destroy_dimension(m.qInfo.qId)
                self.app.do_save()
                return True
        return False

    def update_master_dimension_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], id: str = None, label_expression: str = "") -> bool:
        """Updates an existing master dimension in-place. Returns True if found and updated, False otherwise.
        If id is provided, matches by ID; otherwise matches by name."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {"title": "/qMetaDef/title"}
            }
        })

        layout = dimensions.get_layout()
        for m in layout.qDimensionList.qItems:
            if id is not None and m.qInfo.qId == id or id is None and m.qMeta.title == title:
                dimension_obj = self.app.get_dimension(m.qInfo.qId)
                props = dimension_obj.get_properties()
                props.qDim.qFieldDefs = [definition]
                props.qDim.qFieldLabels = [label or title]
                props.qDim.qLabelExpression = label_expression
                props.qMetaDef.title = title
                props.qMetaDef.description = description
                props.qMetaDef.tags = tags
                dimension_obj.set_properties(props)
                self.app.do_save()
                return True
        return False

    def create_master_dimension_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], label_expression: str = "") -> None:
        """Creates a master dimension and saves it to the app."""

        self.app.create_dimension({
            "qInfo": {
                "qType": "dimension"
            },
            "qDim": {
                "qFieldDefs": [definition],
                "qFieldLabels": [label or title],
                "qLabelExpression": label_expression,
                "qGrouping": "N",
            },
            "qMetaDef": {
                "title": title,
                "description": description,
                "tags": tags,
            }
        })

        self.app.do_save()

    def create_dimensions(self) -> None:
        """Loads dimensions from dimensions.json and creates or updates them. Skips and logs duplicates."""

        with open(self.save_dir / "dimensions.json", "r", encoding="utf-8") as f:
            dimensions = json.load(f)

        duplicates_path = self.save_dir / "dimensions_duplicates.json"

        for dimension in dimensions:
            args = dict(
                title=dimension["title"],
                definition=dimension["definition"],
                description=dimension.get("description", ""),
                label=dimension.get("label", ""),
                tags=dimension.get("tags", []),
                id=dimension.get("id", None),
                label_expression=dimension.get("label_expression", ""),
            )

            matches = self.master_dimension_exists(dimension["title"], dimension.get("id"))

            if len(matches) == 0:
                print(f"Creating: '{dimension['title']}' ✅")
                create_args = {k: v for k, v in args.items() if k != "id"}
                self.create_master_dimension_expr(**create_args)
            elif len(matches) == 1:
                print(f"Updating: '{dimension['title']}' ✅")
                self.update_master_dimension_expr(**args)
            else:
                print(f"⚠️ WARNING: {len(matches)} duplicates found for '{dimension['title']}' — skipping. Written to dimensions_duplicates.json")
                raw = duplicates_path.read_text(encoding="utf-8").strip() if duplicates_path.exists() else ""
                existing = json.loads(raw) if raw else []
                existing_ids = {m["id"] for entry in existing for m in entry.get("qlik_matches", [])}
                new_matches = [m for m in matches if m["id"] not in existing_ids]
                if new_matches:
                    existing.append({
                        "source": dimension,
                        "qlik_matches": new_matches,
                    })
                    duplicates_path.write_text(json.dumps(existing, indent=4), encoding="utf-8")

    def get_measures(self) -> list[dict]:
        """Returns a list of all measures in the app."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qMeasure": "/qMeasure",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = measures.get_layout()
        measures_list = [
            {
                "title":       m.qMeta.title,
                "id":          m.qInfo.qId,
                "description": m.qMeta.description,
                "definition":  m.qData.qMeasure.get("qDef", ""),
                "label":       m.qData.qMeasure.get("qLabelExpression", ""),
                "fmt":         m.qData.qMeasure.get("qNumFormat", {}).get("qFmt", ""),
                "tags":        getattr(m.qData, "tags", []),
            }
            for m in layout.qMeasureList.qItems    
        ]
        
        measures_list.sort(key=lambda x: x["title"], reverse=False)  


        self.save_dir.mkdir(parents=True, exist_ok=True)
        with open(self.save_dir / "measures.json", "w", encoding="utf-8") as f:
            json.dump(measures_list, f, indent=4)
        
        print("✅ Measures fetched successfully!")


    def publish_app(self) -> None:
        """Publish the shared space app to its managed space counterpart."""
        base_url = self.tenant_host.rstrip("/") + "/api/v1"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Resolve the item ID for the shared app
        url = f"{base_url}/items?resourceId={self.app_id}&resourceType=app"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("data", [])
        if not items:
            raise ValueError(f"No item found for app {self.app_id}")
        app_item_id = items[0]["id"]

        # Resolve the published (managed) app ID
        url = f"{base_url}/items/{app_item_id}/publisheditems"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        published = response.json().get("data", [])
        if not published or "resourceId" not in published[0]:
            raise ValueError(
                "Published app not found. If this app has never been published, publish it once from the UI first."
            )
        target_id = published[0]["resourceId"]

        # Publish shared → managed
        url = f"{base_url}/apps/{self.app_id}/publish"
        response = requests.put(url, headers=headers, json={"targetId": target_id})
        response.raise_for_status()
        name = response.json().get("attributes", {}).get("name", self.app_id)
        print(f"✅ '{name}' published successfully")

    def get_dimensions(self) -> list[dict]:
        """Returns a list of all master dimensions in the app."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qDim": "/qDim",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = dimensions.get_layout()
        dimensions_list = [
            {
                "title":       m.qMeta.title,
                "id":          m.qInfo.qId,                
                "description": m.qMeta.description,
                "definition":        (m.qData.qDim.get("qFieldDefs") or [""])[0],
                "label":             (m.qData.qDim.get("qFieldLabels") or [""])[0],
                "label_expression":  m.qData.qDim.get("qLabelExpression", ""),
                "tags":              getattr(m.qData, "tags", []),
            }
            for m in layout.qDimensionList.qItems
        ]
        
        dimensions_list.sort(key=lambda x: x["title"], reverse=False)


        self.save_dir.mkdir(parents=True, exist_ok=True)
        with open(self.save_dir / "dimensions.json", "w", encoding="utf-8") as f:
            json.dump(dimensions_list, f, indent=4)
        
        print("✅ Dimensions fetched successfully!")
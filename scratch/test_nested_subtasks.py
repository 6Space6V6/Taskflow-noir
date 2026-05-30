import unittest
import json
from app import app, db, Project, SubTask

class TestNestedSubtasks(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Seed project
            self.p = Project(title="Mega Project", category="General", priority="Medium")
            db.session.add(self.p)
            db.session.commit()
            self.project_id = self.p.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_add_subtask_and_nesting(self):
        # 1. Add flat Subtask A (parent_id = None)
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Checklist A", "is_side_project": False})
        self.assertEqual(r1.status_code, 200)
        sub_a_id = json.loads(r1.data)['id']

        # 2. Add flat Subtask B (parent_id = None)
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Checklist B", "is_side_project": False})
        self.assertEqual(r2.status_code, 200)
        sub_b_id = json.loads(r2.data)['id']

        # 3. Swap order of Subtask B to index 0 under parent None
        rm = self.client.post(f'/move_subtask/{sub_b_id}', json={"new_parent_id": None, "new_project_id": self.project_id, "new_index": 0})
        self.assertEqual(rm.status_code, 200)

        with app.app_context():
            sub_a = SubTask.query.get(sub_a_id)
            sub_b = SubTask.query.get(sub_b_id)
            self.assertEqual(sub_b.order_index, 0)
            self.assertEqual(sub_a.order_index, 1)

    def test_cannot_have_children_under_subtask(self):
        # Checklist Subtask A
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Checklist Subtask A", "is_side_project": False})
        sub_a_id = json.loads(r1.data)['id']

        # Checklist Subtask B
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Checklist Subtask B", "is_side_project": False})
        sub_b_id = json.loads(r2.data)['id']

        # Try to move Subtask B under Subtask A (cross-branch move, must be blocked)
        rm = self.client.post(f'/move_subtask/{sub_b_id}', json={"new_parent_id": sub_a_id, "new_project_id": self.project_id})
        self.assertEqual(rm.status_code, 400)
        self.assertIn("movement is restricted", json.loads(rm.data)['message'].lower())

    def test_circular_reference_prevention(self):
        # Grandparent Side Project
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Grandparent SP", "is_side_project": True})
        gp_id = json.loads(r1.data)['id']

        # Parent Side Project (created directly under gp_id)
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Parent SP", "is_side_project": True, "parent_id": gp_id})
        p_id = json.loads(r2.data)['id']

        # Child Checklist Subtask (created directly under p_id)
        r3 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Child Subtask", "is_side_project": False, "parent_id": p_id})
        c_id = json.loads(r3.data)['id']

        # Try to move Grandparent SP under Child Checklist Subtask (cross-branch move, must fail)
        rc = self.client.post(f'/move_subtask/{gp_id}', json={"new_parent_id": c_id, "new_project_id": self.project_id})
        self.assertEqual(rc.status_code, 400)
        self.assertIn("movement is restricted", json.loads(rc.data)['message'].lower())

        # Child SP (created directly under p_id)
        r4 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Child SP", "is_side_project": True, "parent_id": p_id})
        csp_id = json.loads(r4.data)['id']

        # Try to move Grandparent SP under Child SP (cross-branch move, must fail)
        rc2 = self.client.post(f'/move_subtask/{gp_id}', json={"new_parent_id": csp_id, "new_project_id": self.project_id})
        self.assertEqual(rc2.status_code, 400)
        self.assertIn("movement is restricted", json.loads(rc2.data)['message'].lower())

    def test_progress_calculation(self):
        # Create 1 Side Project
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Side Project", "is_side_project": True})
        sp_id = json.loads(r1.data)['id']

        # Create 2 Checklist Subtasks directly under it
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Subtask A", "is_side_project": False, "parent_id": sp_id})
        sub_a_id = json.loads(r2.data)['id']

        r3 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Subtask B", "is_side_project": False, "parent_id": sp_id})
        sub_b_id = json.loads(r3.data)['id']

        # Complete Subtask A
        with app.app_context():
            sub_a = SubTask.query.get(sub_a_id)
            sub_a.is_completed = True
            db.session.commit()
            
            p = Project.query.get(self.project_id)
            # The progress calculation: completed subtasks / total subtasks (excluding side projects)
            # Here: 1 completed / 2 total = 50%
            self.assertEqual(p.progress, 50)

    def test_export_import_hierarchy(self):
        # 1. Create a nested setup directly
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Parent SP", "is_side_project": True})
        p_id = json.loads(r1.data)['id']
        
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Child Checklist", "is_side_project": False, "parent_id": p_id})
        c_id = json.loads(r2.data)['id']

        # 2. Export
        rx = self.client.get('/export_data')
        export_json = rx.data.decode('utf-8')
        
        # Verify parent_id is in export
        data = json.loads(export_json)
        subs = data['tables']['subtasks']
        child_export = next(s for s in subs if s['title'] == 'Child Checklist')
        self.assertEqual(child_export['parent_id'], p_id)
        self.assertFalse(child_export['is_side_project'])

        # 3. Clear data
        with app.app_context():
            db.drop_all()
            db.create_all()

        # 4. Import
        import io
        ri = self.client.post('/import_data', data={
            'file': (io.BytesIO(export_json.encode('utf-8')), 'backup.json')
        }, content_type='multipart/form-data')
        self.assertEqual(ri.status_code, 200)

        # Verify hierarchy is restored correctly with newly generated SQLite IDs
        with app.app_context():
            all_subs = SubTask.query.all()
            parent = next(s for s in all_subs if s.title == 'Parent SP')
            child = next(s for s in all_subs if s.title == 'Child Checklist')
            self.assertEqual(child.parent_id, parent.id)
            self.assertTrue(parent.is_side_project)
            self.assertFalse(child.is_side_project)

    def test_add_project_with_nested_hierarchy(self):
        # We send a POST to /add_project with nested structure
        data = {
            "title": "Project with Hierarchy",
            "due_date": "2026-05-20",
            "priority": "Normal",
            "category": "Testing",
            "tags": "test, hierarchy",
            "notes": "Testing recursive creation",
            "subtasks": [
                {
                    "id": "temp_parent_sp",
                    "title": "Parent SP",
                    "is_side_project": True,
                    "parent_id": None
                },
                {
                    "id": "temp_child_sub",
                    "title": "Child Subtask",
                    "is_side_project": False,
                    "parent_id": "temp_parent_sp"
                },
                {
                    "id": "temp_flat_sub",
                    "title": "Flat Subtask",
                    "is_side_project": False,
                    "parent_id": None
                }
            ]
        }
        r = self.client.post('/add_project', json=data)
        self.assertEqual(r.status_code, 200)
        proj_id = json.loads(r.data)['id']

        with app.app_context():
            proj = Project.query.get(proj_id)
            self.assertEqual(proj.title, "Project with Hierarchy")
            self.assertEqual(len(proj.subtasks), 3)

            parent = next(s for s in proj.subtasks if s.title == "Parent SP")
            child = next(s for s in proj.subtasks if s.title == "Child Subtask")
            flat = next(s for s in proj.subtasks if s.title == "Flat Subtask")

            self.assertTrue(parent.is_side_project)
            self.assertFalse(child.is_side_project)
            self.assertFalse(flat.is_side_project)

            self.assertEqual(child.parent_id, parent.id)
            self.assertIsNone(parent.parent_id)
            self.assertIsNone(flat.parent_id)

    def test_drag_drop_same_parent_validation_ok(self):
        # 1. Create a side project
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Folder SP", "is_side_project": True})
        sp_id = json.loads(r1.data)['id']

        # 2. Create SubA directly under Folder SP
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "SubA", "is_side_project": False, "parent_id": sp_id})
        sub_a_id = json.loads(r2.data)['id']

        # 3. Moving SubA under Folder SP again (same parent) should be allowed (returns 200)
        rm = self.client.post(f'/move_subtask/{sub_a_id}', json={"new_parent_id": sp_id, "new_project_id": self.project_id, "new_index": 0})
        self.assertEqual(rm.status_code, 200)

    def test_drag_drop_cross_parent_validation_fails(self):
        # 1. Create a side project
        r1 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Folder A", "is_side_project": True})
        sp_a_id = json.loads(r1.data)['id']

        # 2. Create another side project
        r2 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "Folder B", "is_side_project": True})
        sp_b_id = json.loads(r2.data)['id']

        # 3. Create a checklist subtask under Folder A
        r3 = self.client.post(f'/add_subtask/{self.project_id}', json={"title": "SubA", "is_side_project": False})
        sub_a_id = json.loads(r3.data)['id']
        self.client.post(f'/move_subtask/{sub_a_id}', json={"new_parent_id": sp_a_id, "new_project_id": self.project_id})

        # 4. Try to drag SubA under Folder B (cross-parent/different branch). This should FAIL (returns 400).
        rm = self.client.post(f'/move_subtask/{sub_a_id}', json={"new_parent_id": sp_b_id, "new_project_id": self.project_id})
        self.assertEqual(rm.status_code, 400)
        self.assertIn("Movement is restricted", json.loads(rm.data)['message'])

    def test_add_side_project_quick_endpoint(self):
        # 1. POST to /add_side_project/<project_id>
        data = {
            "title": "Quick Side Project",
            "subtasks": ["Checklist Item 1", "Checklist Item 2", "  "]
        }
        r = self.client.post(f'/add_side_project/{self.project_id}', json=data)
        self.assertEqual(r.status_code, 200)
        sp_id = json.loads(r.data)['id']

        # 2. Verify in DB
        with app.app_context():
            sp = SubTask.query.get(sp_id)
            self.assertEqual(sp.title, "Quick Side Project")
            self.assertTrue(sp.is_side_project)
            self.assertIsNone(sp.parent_id)
            self.assertEqual(sp.project_id, self.project_id)

            # Check children
            children = sp.children
            self.assertEqual(len(children), 2)
            self.assertEqual(children[0].title, "Checklist Item 1")
            self.assertFalse(children[0].is_side_project)
            self.assertEqual(children[1].title, "Checklist Item 2")

if __name__ == '__main__':
    unittest.main()

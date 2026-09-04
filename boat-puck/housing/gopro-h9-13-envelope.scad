// Boat Puck — GoPro HERO9–13 housing
// Doctrine: housing cavity = camera positive (mold clearance = microns).
// Units: mm
//
// camera_positive()     — exact published chassis envelope
// lens_boss()           — stock protective lens protrusion (GPS pocket)
// camera_with_lens()    — body box + front lens boss
// print_slip_dummy()    — optional −0.15 mm/side for FDM drop-fit only

/* [Camera positive = cavity] */
cam_W = 71.8;
cam_H = 50.8;
cam_D = 33.6;

/* [Stock protective lens — GPS pocket] */
// Community / accessory fit (medium confidence) — caliper before PCB freeze
lens_OD = 33.0;          // approx outer diameter
lens_square = 31.5;      // alternate square footprint listing
lens_protrusion = 5.5;   // past front face; range 5.0–6.0
// Body depth behind lens tip ≈ cam_D - lens_protrusion

/* [Optional FDM slip — NOT cavity uncertainty] */
slip_per_side = 0.15;
slip_depth_total = 0.30;

$fn = 64;

module camera_body_box() {
  // Envelope includes lens in published D; for boss modeling we optionally
  // shorten the box so the lens cylinder is explicit at the front.
  cube([cam_W, cam_H, cam_D], center = true);
}

module camera_body_behind_lens() {
  // Body only: total D minus lens protrusion (lens tip at -Z extreme)
  d = cam_D - lens_protrusion;
  translate([0, 0, lens_protrusion / 2])
    cube([cam_W, cam_H, d], center = true);
}

module lens_boss() {
  // Front protective lens stick-out — housing tunnel / GPS antenna well
  // −Z is lens / housing glass direction
  translate([0, 0, -cam_D / 2 + lens_protrusion / 2])
    cylinder(h = lens_protrusion, d = lens_OD, center = true);
}

module camera_with_lens() {
  union() {
    camera_body_behind_lens();
    lens_boss();
  }
}

module gps_antenna_keep_in() {
  // Usable antenna volume inside lens tunnel (design target)
  translate([0, 0, -cam_D / 2 + 5.5 / 2])
    cylinder(h = 5.5, d = 30.0, center = true);
}

module print_slip_dummy() {
  cube([
    cam_W - 2 * slip_per_side,
    cam_H - 2 * slip_per_side,
    cam_D - slip_depth_total
  ], center = true);
}

module marked_positive() {
  difference() {
    camera_with_lens();
    translate([0, cam_H / 2 - 1.2, -cam_D / 2 + lens_protrusion + 1.0])
      cube([10, 2.4, 2], center = true);
  }
}

// Default preview: body + lens boss (GPS pocket highlighted)
color([0.2, 0.55, 0.95, 0.45]) camera_body_behind_lens();
color([0.95, 0.55, 0.15, 0.75]) lens_boss();
color([0.2, 0.8, 0.3, 0.35]) gps_antenna_keep_in();

// Uncomment to export STL:
// marked_positive();
// camera_with_lens();
// print_slip_dummy();

echo(str("CAVITY = CAMERA positive mm: ", cam_W, " x ", cam_H, " x ", cam_D));
echo(str("LENS protrusion mm: ", lens_protrusion, "  OD: ", lens_OD));
echo(str("GPS pocket target: Ø30 x 5.5 mm"));

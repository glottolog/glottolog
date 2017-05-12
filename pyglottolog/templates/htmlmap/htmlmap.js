var geojson = $geojson;
var markers = [],
    families = {},
    flayers = {},
    map = L.map('map', {fullscreenControl: true}).setView([5, 160], 2);

var OpenStreetMap_BlackAndWhite = L.tileLayer('http://{s}.tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
});
OpenStreetMap_BlackAndWhite.addTo(map);

function onEachFeature(feature, layer) {
    var fid = feature.properties.family_id,
        html = "<h3>" + feature.properties.name + "</h3><dl>";
    html += '<dt>Glottocode:</dt><dd><a href="http://glottolog.org/resource/languoid/id/' + feature.id + '">' + feature.id + '</a></dd>';
    html += "<dt>Family</dt><dd>" + feature.properties.family + "</dd>";
    html += "</dl>";
    layer.bindPopup(html);
    if (geojson.properties.legend.hasOwnProperty(fid)) {
        if (families.hasOwnProperty(fid)) {
            families[fid].push(layer);
        } else {
            families[fid] = [];
        }
    }
    layer.bindTooltip(feature.properties.name);
    markers.push(layer);
}
L.geoJSON([geojson], {
    onEachFeature: onEachFeature,
    pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, {
            radius: 5,
            fillColor: '#' + feature.properties.color,
            color: "#000",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
        });
    }
}).addTo(map);

var group = new L.featureGroup(markers);
map.fitBounds(group.getBounds());

for (var fid in families) {
    if (families.hasOwnProperty(fid)) {
        flayers[geojson.properties.legend[fid]] = L.layerGroup(families[fid]);
        flayers[geojson.properties.legend[fid]].addTo(map);
    }
}
L.control.layers({}, flayers).addTo(map);
